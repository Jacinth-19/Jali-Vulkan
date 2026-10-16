#!/usr/bin/env python3
"""Development-only local neural speech + WebGL face studio; no upload/cloud API.

Run after build_neural_studio.py. One bounded job at a time; six ready sessions
retained in this run. The request token/origin policy prevents browser CSRF, NOT
remote-user authentication. Do not expose as a public service or enter secrets.
"""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
import socket
from pathlib import Path
import secrets
import shutil
import threading
from urllib.parse import urlparse,parse_qs
import uuid

from analyze_neural_clips import digest, verify_engine
from neural_platform import analyzer_path
from local_neural_speech import validate_request, verify_assets
from neural_session import build_session, SESSION_ID, MEDIA, ROOT
from neural_cancel import CancellationToken, GenerationCancelled
from neural_stream import sentence_batches, perform_stream, MAX_CHUNKS, MAX_STREAM_CHARACTERS
from preview_server import Handler as FileHandler
from http.server import ThreadingHTTPServer

STATIC = {'/': 'index.html', '/style.css': 'style.css', '/controller.js': 'controller.js',
          '/viewer.js': 'viewer.js', '/demo-data.js': 'demo-data.js',
          '/rig.json': 'rig.json', '/licenses/model-source-README.md': 'licenses/model-source-README.md'}


class StudioState:
    def __init__(self, directory, rig, rhubarb, pipeline=build_session):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.rig, self.rhubarb, self.pipeline = rig, rhubarb, pipeline
        self.native = None
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.streams = {}
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.jobs = {}
        self.tokens = {}
        self.ready = []
        self.failed = []
        self.busy = False
        self.token = secrets.token_hex(32)

    def start(self, text, streaming=False):
        if not streaming:validate_request(text)
        batches=sentence_batches(text) if streaming else None
        with self.lock:
            if self.busy:
                return None
            self.busy = True
            ident = uuid.uuid4().hex
            self.jobs[ident] = {'state': 'running', 'stage': 'queued', 'id': ident}
            self.tokens[ident] = CancellationToken()
            if streaming:
                self.streams[ident]={'pending':[],'consumed':0,'produced':0}
                self.jobs[ident].update(mode='sentence-batched',chunks=[],chunk_count=len(batches),consumed=0,produced=0)
        if streaming:self.pool.submit(perform_stream,self,ident,text,batches)
        else:self.pool.submit(self.perform, ident, text)
        return ident

    def cancel(self, ident):
        with self.lock:
            token = self.tokens.get(ident)
            if token is None or self.jobs.get(ident,{}).get('state') not in ('running','cancelling'):return False
            token.cancel()
            self.jobs[ident] = {'state':'cancelling','stage':'cancelling','id':ident}
            self.condition.notify_all()
            return True

    def acknowledge(self,ident,index):
        with self.condition:
            stream=self.streams.get(ident)
            if stream is None or self.jobs[ident]['state']!='running':return False
            if index<stream['consumed']:return True
            if not stream['pending'] or stream['pending'][0]['index']!=index:return False
            old=stream['pending'].pop(0);self.jobs.pop(old['id'],None)
            stream['consumed']+=1;self.jobs[ident].update(chunks=list(stream['pending']),consumed=stream['consumed'])
            self.condition.notify_all();return True

    def cancel_active(self):
        with self.lock:
            for token in self.tokens.values():token.cancel()

    def perform(self, ident, text):
        token = self.tokens[ident]
        def stage(value):
            with self.lock:
                token.check()
                self.jobs[ident] = {'state': 'running', 'stage': value, 'id': ident}
        stage.cancel_token = token
        try:
            token.check()
            clip = self.pipeline(ident, text, self.root / ident, self.rig, self.rhubarb, stage)
            with self.lock:
                token.check()
                self.tokens.pop(ident,None);self.busy=False
                self.jobs[ident] = {'state': 'ready', 'stage': 'ready', 'id': ident, 'clip': clip}
                self.ready.append(ident)
                while len(self.ready) > 6:
                    old = self.ready.pop(0)
                    self.jobs.pop(old, None)
                    shutil.rmtree(self.root / old, ignore_errors=True)
        except Exception as error:
            shutil.rmtree(self.root / ident, ignore_errors=True)
            with self.lock:
                self.tokens.pop(ident,None);self.busy=False
                if isinstance(error, GenerationCancelled) or token.event.is_set():
                    self.jobs[ident] = {'state':'cancelled','stage':'cancelled','id':ident}
                else:
                    self.jobs[ident] = {'state': 'error', 'stage': 'error', 'id': ident,
                        'error': f'Local generation/analysis failed ({type(error).__name__}). No substitute audio or cues were used. Try a shorter English sentence.'}
                self.failed.append(ident)
                while len(self.failed)>6:self.jobs.pop(self.failed.pop(0),None)
        finally:
            with self.lock:
                if self.tokens.pop(ident, None) is not None:self.busy = False

    def get(self, ident):
        with self.lock:
            data = self.jobs.get(ident)
            return copy.deepcopy(data) if data else None


class Handler(FileHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def do_POST(self):
        if self.path not in ('/api/generate','/api/cancel','/api/stream','/api/ack'):
            return self.json_response(404, {'error': 'Not found'})
        origin = self.headers.get('Origin')
        try:
            if origin and (urlparse(origin).scheme not in ('http', 'https') or urlparse(origin).netloc != self.headers.get('Host')):
                return self.json_response(403, {'error': 'Same-origin requests only'})
        except ValueError:
            return self.json_response(403, {'error': 'Invalid origin'})
        if not secrets.compare_digest(self.headers.get('X-Jali-Token', '').encode('utf-8'), self.server.state.token.encode('ascii')):
            return self.json_response(403, {'error': 'Refresh the page to obtain its request token'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192 or self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                raise ValueError('Expected a small JSON body with Content-Length')
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError('Incomplete request')
            payload = json.loads(body)
            expected = {'text'} if self.path in ('/api/generate','/api/stream') else {'id','index'} if self.path=='/api/ack' else {'id'}
            if not isinstance(payload, dict) or set(payload) != expected:
                raise ValueError('Unexpected request fields')
            if self.path in ('/api/generate','/api/stream'):
                if self.path=='/api/stream':sentence_batches(payload['text'])
                else:validate_request(payload['text'])
            elif not isinstance(payload['id'],str) or not SESSION_ID.fullmatch(payload['id']):
                raise ValueError('Invalid job identity')
            if self.path=='/api/ack' and (isinstance(payload['index'],bool) or not isinstance(payload['index'],int) or not 0<=payload['index']<MAX_CHUNKS):raise ValueError('Invalid chunk index')
        except (ValueError, UnicodeError) as error:
            return self.json_response(400, {'error': str(error)})
        if self.path == '/api/cancel':
            if not self.server.state.get(payload['id']):return self.json_response(404, {'error':'Unknown job'})
            if not self.server.state.cancel(payload['id']):return self.json_response(409, {'error':'Job is already finished'})
            return self.json_response(202, {'id':payload['id'],'state':'cancelling'})
        if self.path=='/api/ack':
            if not self.server.state.get(payload['id']):return self.json_response(404,{'error':'Unknown job'})
            if not self.server.state.acknowledge(payload['id'],payload['index']):return self.json_response(409,{'error':'Chunk acknowledgement is out of order or job is finished'})
            return self.json_response(200,{'acknowledged':payload['index']})
        ident = self.server.state.start(payload['text'],streaming=self.path=='/api/stream')
        if ident is None:
            return self.json_response(409, {'error': 'One generation is already running. Please wait.'})
        return self.json_response(202, {'id': ident})

    def do_GET(self, head_only=False):
        route = urlparse(self.path).path
        if route == '/api/config':
            return self.json_response(200, {'token': self.server.state.token, 'max_characters': 500, 'max_stream_characters':MAX_STREAM_CHARACTERS,'max_stream_chunks':MAX_CHUNKS,
                'voice': 'Kokoro af_heart (stock, CPU)', 'rig': self.server.state.rig, 'native':self.server.state.native.metadata if self.server.state.native else None})
        if route=='/api/native/frame':
            if head_only:return self.json_response(405,{'error':'Use GET'})
            origin=self.headers.get('Origin')
            if (origin and urlparse(origin).netloc!=self.headers.get('Host')) or not secrets.compare_digest(self.headers.get('X-Jali-Token','').encode(),self.server.state.token.encode()):return self.json_response(403,{'error':'Same-origin token required'})
            if self.server.state.native is None:return self.json_response(404,{'error':'Native renderer not enabled'})
            q=parse_qs(urlparse(self.path).query,keep_blank_values=True)
            if not {'id','time'}<=q.keys() or q.keys()-{'id','time','trim','mood','life','gaze','sync','resolution','articulation'} or any(len(v)!=1 for v in q.values()):return self.json_response(400,{'error':'Invalid native frame query'})
            clip={'state':'ready','clip':{'rig':self.server.state.rig,'duration':0,'cues':[]}} if q['id'][0]=='neutral' else self.server.state.get(q['id'][0])
            if not clip or clip['state']!='ready':return self.json_response(404,{'error':'Unknown/expired native session'})
            try:body,ms=self.server.state.native.frame(clip['clip'],q)
            except (ValueError,KeyError):return self.json_response(400,{'error':'Invalid native frame input'})
            except BlockingIOError:return self.json_response(409,{'error':'One native frame already pending'})
            except Exception:return self.json_response(503,{'error':'Native renderer stopped; restart the development server'})
            self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Jali-Render-Ms',f'{ms:.3f}');self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
            return
        if route.startswith('/api/jobs/'):
            ident = route[len('/api/jobs/'):]
            result = self.server.state.get(ident) if SESSION_ID.fullmatch(ident) else None
            return self.json_response(200 if result else 404, result or {'error': 'Unknown/expired job'})
        if route in STATIC:
            return self.send_file(self.server.assets / STATIC[route], head_only)
        parts = route.split('/')
        if len(parts) == 4 and parts[1] == 'sessions' and SESSION_ID.fullmatch(parts[2]) and parts[3] in MEDIA:
            result = self.server.state.get(parts[2])
            if result and result['state'] == 'ready':
                return self.send_file(self.server.state.root / parts[2] / parts[3], head_only)
        if route == '/favicon.ico':
            self.send_response(204); self.end_headers(); return
        return self.json_response(404, {'error': 'Not found'})


class StudioHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(assets, state, host='0.0.0.0', port=8082):
    server = StudioHTTPServer((host, port), Handler)
    server.assets, server.state = Path(assets), state
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8082)
    parser.add_argument('--bind', default='0.0.0.0')
    parser.add_argument('--sessions', type=Path, help='Explicit session store for isolated benchmarks')
    parser.add_argument('--native-asset',type=Path,help='Optional decoded rich-v1 native GLB')
    parser.add_argument('--software-vulkan',action='store_true')
    parser.add_argument('--ready-file', type=Path, help='Write actual bound port after readiness')
    args = parser.parse_args()
    assets = ROOT / 'artifacts/neural-studio'
    required = ['index.html', 'viewer.js', 'controller.js', 'demo-data.js', 'rig.json']
    if not all((assets / name).is_file() for name in required):
        parser.error('Run tools/build_neural_studio.py first')
    rig = json.loads((assets / 'rig.json').read_text())
    if digest(assets / 'viewer.js') != rig['viewer_sha256'] or digest(assets / 'model/mpfb-head.glb') != rig['model_sha256']:
        parser.error('Studio assets changed: rerun build_neural_studio.py')
    verify_assets(ROOT / 'models/kokoro')
    rhubarb = analyzer_path()
    try:
        verify_engine(rhubarb)
    except ValueError as error:
        parser.error(str(error))
    sessions = args.sessions or ROOT / 'artifacts/neural-studio-sessions'
    sessions.mkdir(parents=True, exist_ok=True)
    state = StudioState(sessions, rig, rhubarb)
    # Bind before deleting stale sessions: a second instance must not erase the
    # first instance's recordings when its port is already occupied.
    try:
        server = make_server(assets, state, args.bind, args.port)
    except BaseException:
        state.pool.shutdown(wait=True)
        raise
    try:
        if args.native_asset:
            from native_studio import NativeStudio
            state.native=NativeStudio(args.native_asset.resolve(),rig,args.software_vulkan)
        for old in sessions.iterdir():
            if old.is_dir() and SESSION_ID.fullmatch(old.name):
                shutil.rmtree(old)
        if args.ready_file:
            args.ready_file.write_text(json.dumps({'port':server.server_address[1]}), encoding='utf-8')
    except BaseException:
        server.server_close(); state.pool.shutdown(wait=True)
        if state.native:state.native.close()
        raise
    print(f'Local neural face studio on {args.bind}:{server.server_address[1]}; CPU only; development server', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.cancel_active()
        state.pool.shutdown(wait=True)
        if state.native:state.native.close()


if __name__ == '__main__':
    main()
