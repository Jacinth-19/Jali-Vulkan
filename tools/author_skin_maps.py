"""Build-only authored UV-bake recipe. Synthetic, NOT scanned or hand-painted skin.

Anatomical roughness zones and gentle pigmentation are authored in rest-space;
UV rasterization makes them stable under deformation. Normal microdetail is still
procedural. No photographs, external textures, training data or runtime work.
"""
import argparse
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image

VERSION='jali-authored-skin-recipe-v1'
SIZE=512


def bake(data, albedo):
    p=np.asarray(data['positions'],dtype=np.float64);uv=np.asarray(data['uv'],dtype=np.float64)
    tri=np.asarray(data['indices'],dtype=np.int64).reshape(-1,3)
    if p.shape!=(len(uv),3) or uv.shape[1]!=2 or len(p)>100000 or len(tri)>160000 or not np.isfinite(p).all() or not np.isfinite(uv).all() or np.any(tri<0) or np.any(tri>=len(p)):raise ValueError('Invalid bounded UV bake input')
    world=np.zeros((SIZE,SIZE,3));covered=np.zeros((SIZE,SIZE),bool)
    for ids in tri:
        t=uv[ids]*(SIZE-1);lo=np.maximum(0,np.floor(t.min(axis=0)).astype(int));hi=np.minimum(SIZE-1,np.ceil(t.max(axis=0)).astype(int))
        if (hi<lo).any():continue
        a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10:continue
        yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w=1-u-v
        inside=(u>=-1e-6)&(v>=-1e-6)&(w>=-1e-6)
        pos=u[...,None]*p[ids[0]]+v[...,None]*p[ids[1]]+w[...,None]*p[ids[2]]
        view=world[lo[1]:hi[1]+1,lo[0]:hi[0]+1];view[inside]=pos[inside]
        covered[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=inside
    # Eye pivot is supplied from actual rig, so zones follow male stature/refit.
    eye=float(data['eye_y']);x,y,z=np.moveaxis(world,-1,0)
    face=covered & (y>eye-.13)&(y<eye+.13)&(z>.075)&(np.abs(x)<.105)
    cheek=np.exp(-((np.abs(x)-.043)/.028)**2-((y-(eye-.045))/.036)**2)
    nose=np.exp(-(x/.017)**2-((y-(eye-.027))/.04)**2)
    forehead=np.exp(-(x/.065)**2-((y-(eye+.065))/.035)**2)
    # Deliberately gentle: the source identity/albedo is retained, not recoloured
    # into a different person or asserted to be a calibrated human measurement.
    rgb=np.asarray(albedo.resize((SIZE,SIZE),Image.Resampling.LANCZOS).convert('RGB'),dtype=float)
    tint=np.stack([.985+.012*cheek,.98-.009*cheek,.975-.012*cheek],axis=-1)
    tint[~face]=1
    field=np.asarray(Image.fromarray(np.clip(tint*255,0,255).astype('uint8')).resize((1024,1024),Image.Resampling.BILINEAR))/255
    rgb=np.asarray(albedo.resize((1024,1024),Image.Resampling.LANCZOS).convert('RGB'),dtype=float)*field
    rough=np.full((SIZE,SIZE),.76);rough[face]=(.96+.04*cheek-.11*nose-.06*forehead)[face]
    # Authored faint creases plus bounded synthetic pore height. This is an
    # explicit procedural component; the baked normal is not called a scan.
    yy,xx=np.mgrid[:SIZE,:SIZE];rng=np.random.default_rng(174)
    height=rng.normal(0,.018,(SIZE,SIZE))
    # Smooth bounded microheight; unused UVs retain neutral normal values.
    for _ in range(4):height=(height+np.roll(height,1,0)+np.roll(height,-1,0)+np.roll(height,1,1)+np.roll(height,-1,1))/5
    height*=face
    gy,gx=np.gradient(height);normal=np.stack([-gx*3.5,-gy*3.5,np.ones_like(gx)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    # Alpha is an explicit skin-only thin-region mask for the optional wrap lobe.
    thin=np.where(face,.12+.7*np.exp(-((np.abs(x)-.077)/.019)**2),0)
    n=np.concatenate([np.clip((normal*.5+.5)*255,0,255),np.clip(thin[...,None]*255,0,255)],axis=-1).astype('uint8')
    return Image.fromarray(np.clip(rgb,0,255).astype('uint8')),Image.fromarray(n),Image.fromarray((np.clip(rough,0,1)*255).astype('uint8')).convert('RGB'),{'schema':VERSION,'size':SIZE,'covered_uv_pixels':int(covered.sum()),'face_pixels':int(face.sum()),'normal_detail':'authored recipe with procedural microheight; not scanned or artist hand-painted','roughness':'authored rest-space cheek/nose/forehead zones, not measured skin','scattering_mask':'synthetic thin-region mask in normal alpha; not measured thickness','source_albedo_retained':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('geometry',type=Path);p.add_argument('albedo',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    if a.geometry.stat().st_size>32*1024*1024:raise ValueError('Bake geometry exceeds budget')
    data=json.loads(a.geometry.read_text());albedo=Image.open(a.albedo)
    images=bake(data,albedo);a.output.mkdir(parents=True,exist_ok=True)
    for name,image in zip(('albedo','normal','roughness'),images[:3]):image.save(a.output/(name+'.png'))
    yy,xx=np.mgrid[:128,:128]
    strands=72+12*np.sin(xx*1.9)+6*np.sin(xx*.47+yy*.04)+4*np.sin(xx*4.7+yy*.09)
    hair=np.stack([strands,strands*.72,strands*.49],axis=-1)
    Image.fromarray(np.clip(hair,0,255).astype('uint8')).save(a.output/'hair.png')
    (a.output/'recipe.json').write_text(json.dumps(images[3],indent=2)+'\n')


if __name__=='__main__':main()
