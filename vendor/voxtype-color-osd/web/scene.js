import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';

const TAU=Math.PI*2, LENGTH=24, RADIUS=1.45;
const axis=new THREE.Vector3(0,1,0);
const sphere=new THREE.SphereGeometry(1,16,12);
const cylinder=new THREE.CylinderGeometry(1,1,1,10,1);
const dummy=new THREE.Object3D();
const clip=[new THREE.Plane(new THREE.Vector3(1,0,0),12.12),new THREE.Plane(new THREE.Vector3(-1,0,0),12.12)];

class Helix extends THREE.Curve {
  constructor(strand){super();this.strand=strand;}
  getPoint(u,target=new THREE.Vector3()) {
    const theta=u*TAU*2.1+this.strand*Math.PI;
    return target.set((u-.5)*LENGTH,Math.sin(theta)*RADIUS,Math.cos(theta)*RADIUS);
  }
}
const path=[new Helix(0),new Helix(1)];
function material(color,extra={}) {
  return new THREE.MeshPhysicalMaterial({color,roughness:.26,metalness:.38,clearcoat:.8,
    clearcoatRoughness:.17,envMapIntensity:.18,...extra});
}
function mesh(geometry,mat,group) {
  const item=new THREE.Mesh(geometry,mat);item.castShadow=true;item.receiveShadow=true;
  group.add(item);return item;
}
function rod(a,b,r,mat,group) {
  const item=mesh(cylinder,mat,group);item.position.copy(a).add(b).multiplyScalar(.5);
  item.scale.set(r,a.distanceTo(b),r);
  item.quaternion.setFromUnitVectors(axis,b.clone().sub(a).normalize());return item;
}
function ball(p,r,mat,group,geometry=sphere) {
  const item=mesh(geometry,mat,group);item.position.copy(p);item.scale.setScalar(r);return item;
}
function seeded(i){const x=Math.sin(i*78.233+12.9898)*43758.5453;return x-Math.floor(x);}

export async function createScene(canvas) {
  const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true,alpha:false});
  renderer.setPixelRatio(1);renderer.setSize(696,112,false);
  renderer.setClearColor(0x000000);renderer.localClippingEnabled=true;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.9;
  const scene=new THREE.Scene();scene.background=new THREE.Color(0);
  scene.fog=new THREE.Fog(0x010306,22.9,27.3);
  const environment=new RoomEnvironment();
  const pmrem=new THREE.PMREMGenerator(renderer);
  scene.environment=pmrem.fromScene(environment,.04).texture;
  environment.dispose();pmrem.dispose();
  scene.add(new THREE.HemisphereLight(0x9ac7df,0x080d15,.15));
  const key=new THREE.DirectionalLight(0xffeee0,2.8);key.position.set(-5,7,12);
  key.castShadow=true;key.shadow.mapSize.set(2048,1024);
  Object.assign(key.shadow.camera,{left:-16,right:16,top:7,bottom:-7,near:.1,far:50});
  key.shadow.bias=-.0002;key.shadow.normalBias=.025;scene.add(key);
  const rim=new THREE.DirectionalLight(0x70dbff,1.3);rim.position.set(4,3,-8);scene.add(rim);
  const fill=new THREE.DirectionalLight(0xff9472,.15);fill.position.set(6,-3,8);scene.add(fill);
  const scan=new THREE.PointLight(0x8bdcff,6,5);scene.add(scan);
  const gridPoints=[];
  for(let x=-12;x<=12;x+=1)gridPoints.push(x,-1.8,-2,x,1.8,-2);
  for(let y=-1.5;y<=1.5;y+=.5)gridPoints.push(-12,y,-2,12,y,-2);
  const gridGeometry=new THREE.BufferGeometry();
  gridGeometry.setAttribute('position',new THREE.Float32BufferAttribute(gridPoints,3));
  const grid=new THREE.LineSegments(gridGeometry,new THREE.LineBasicMaterial({color:0x163645}));scene.add(grid);
  const camera=new THREE.PerspectiveCamera(2*Math.atan((28*56/348)/48)*180/Math.PI,348/56,.1,100);
  camera.position.set(0,.6,24);camera.lookAt(0,0,0);
  const iso=new THREE.OrthographicCamera(-14,14,14*56/348,-14*56/348,.1,100);
  iso.position.set(0,7,24);iso.lookAt(0,0,0);
  const composer=new EffectComposer(renderer);
  const renderPass=new RenderPass(scene,camera);composer.addPass(renderPass);
  const bloom=new UnrealBloomPass(new THREE.Vector2(696,112),.0,.25,.8);composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const molecule=await (await fetch('./molecule.json')).json();
  const groups=[];

  function build(index) {
    const group=new THREE.Group();group.visible=false;scene.add(group);
    const pair=index===1?[0xe4b74d,0x0fbea3]:index===6?[0x1bcf96,0xf45255]:[0x03baad,0xed3b65];
    const mats=pair.map(c=>material(c));
    if(index===2) {
      const scale=1.7/molecule.radius,spacing=molecule.halfLength*2*scale;
      const count=Math.ceil(24/spacing)+2;
      const atomColors={C:0xb9c9ce,N:0x4d83ff,O:0xff654d,P:0xffcb54};
      const atoms=[],bonds=[];
      for(let copy=-Math.floor(count/2);copy<=Math.floor(count/2);copy++) {
        const points=molecule.atoms.map(a=>new THREE.Vector3(a[0]*scale+copy*spacing,a[1]*scale,a[2]*scale));
        molecule.atoms.forEach((a,i)=>{if(Math.abs(points[i].x)<12.1)atoms.push({p:points[i],color:atomColors[a[3]]||atomColors.C,r:(a[3]==='P'?1.1:.8)*scale});});
        molecule.bonds.forEach(([a,b])=>{
          if(Math.abs(points[a].x)>12.2||Math.abs(points[b].x)>12.2)return;
          const mid=points[a].clone().add(points[b]).multiplyScalar(.5);
          bonds.push([points[a],mid,atomColors[molecule.atoms[a][3]]||atomColors.C]);
          bonds.push([mid,points[b],atomColors[molecule.atoms[b][3]]||atomColors.C]);
        });
      }
      const atomMesh=new THREE.InstancedMesh(sphere,material(0xffffff,{metalness:.12,clippingPlanes:clip}),atoms.length);
      atoms.forEach((a,i)=>{dummy.position.copy(a.p);dummy.quaternion.identity();dummy.scale.setScalar(a.r);dummy.updateMatrix();atomMesh.setMatrixAt(i,dummy.matrix);atomMesh.setColorAt(i,new THREE.Color(a.color));});
      atomMesh.castShadow=true;atomMesh.receiveShadow=true;group.add(atomMesh);
      const bondMesh=new THREE.InstancedMesh(cylinder,material(0xffffff,{roughness:.4,clippingPlanes:clip}),bonds.length);
      bonds.forEach(([a,b,color],i)=>{dummy.position.copy(a).add(b).multiplyScalar(.5);dummy.scale.set(.035,a.distanceTo(b),.035);dummy.quaternion.setFromUnitVectors(axis,b.clone().sub(a).normalize());dummy.updateMatrix();bondMesh.setMatrixAt(i,dummy.matrix);bondMesh.setColorAt(i,new THREE.Color(color));});
      group.add(bondMesh);return group;
    }
    if(index===7) {
      const count=3600;
      const particles=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1,1),material(0xffffff,{roughness:.35,metalness:.2}),count);
      for(let i=0;i<count;i++) {
        const strand=i%2,u=seeded(i+1),p=path[strand].getPoint(u);
        const a=seeded(i+300)*TAU,r=Math.sqrt(seeded(i+800))*.25;
        p.y+=Math.sin(a)*r;p.z+=Math.cos(a)*r;p.x+=(seeded(i+1600)-.5)*.12;
        if(i%9===0){p.y*=seeded(i+99);p.z*=seeded(i+99);}
        dummy.position.copy(p);dummy.quaternion.identity();dummy.scale.setScalar(.025+seeded(i+1200)*.04);dummy.updateMatrix();particles.setMatrixAt(i,dummy.matrix);
        particles.setColorAt(i,new THREE.Color(strand===0?0x4be5d2:(i%3?0xf7d269:0xf69f9b)));
      }
      particles.castShadow=true;particles.receiveShadow=true;group.add(particles);return group;
    }
    if(index===3){mats.forEach(m=>{m.color.set(0x82dcff);m.roughness=.55;m.metalness=.05;});}
    if(index===4){mats[0].color.set(0x10d8dd);mats[1].color.set(0xff397c);mats.forEach(m=>{m.emissive.copy(m.color);m.emissiveIntensity=.35;});}
    if(index===5){mats[0].color.set(0x70daff);mats[1].color.set(0xffba59);}
    if(index===8){mats[0].color.set(0xc2e6eb);mats[1].color.set(0xbca7df);mats.forEach(m=>{m.metalness=.94;m.roughness=.14;m.envMapIntensity=1.2;});}
    if(index===9){mats[0].color.set(0x47bfff);mats[1].color.set(0xafa0fa);mats.forEach(m=>{m.emissive.copy(m.color);m.emissiveIntensity=.14;});}
    for(let strand=0;strand<2;strand++) {
      const radius=index===1?.29:index===3?.115:index===5?.16:index===9?.19:.245;
      const geometry=new THREE.TubeGeometry(path[strand],240,radius,index===6?5:12,false);
      if(index===6){mats[strand].flatShading=true;mats[strand].roughness=.52;}
      const body=mesh(geometry,mats[strand],group);
      if(index===8)body.userData.original=new Float32Array(geometry.attributes.position.array);
      if(index===5) {
        body.material=material(strand?0x2d1b12:0x0d252e,{roughness:.8,metalness:0});
        mesh(new THREE.TubeGeometry(path[strand],64,.24,6,false),material(strand?0xffba59:0x70daff,{wireframe:true,roughness:.5,emissive:strand?0x44240b:0x063a52,emissiveIntensity:.2}),group);
      }
      if(index===9) {
        const shell=material(strand?0xbd9bff:0x50ddff,{transparent:true,opacity:.22,roughness:.2,metalness:.1,emissive:strand?0x9479ff:0x20bddd,emissiveIntensity:.7,depthWrite:false});
        mesh(new THREE.TubeGeometry(path[strand],160,.285,10,false),shell,group);
      }
      if(index===4)for(const radius of [.30,.38]) {
        mesh(new THREE.TubeGeometry(path[strand],160,radius,10,false),
          new THREE.MeshBasicMaterial({color:mats[strand].color,transparent:true,opacity:.055,
            blending:THREE.AdditiveBlending,depthWrite:false}),group);
      }
      if(index===0||index===6||index===8)for(let i=0;i<=24;i++)ball(path[strand].getPoint(i/24),index===8?.27:.29,mats[strand],group,index===6?new THREE.IcosahedronGeometry(1,0):sphere);
      else for(const u of [0,1])ball(path[strand].getPoint(u),radius,mats[strand],group);
      if(index===3||index===9)for(let i=0;i<=42;i++) {
        const ring=mesh(new THREE.TorusGeometry(index===3?.16:.25,.013,4,16),material(index===3?0xd3f5ff:0x8bddff,{emissive:0x225576,emissiveIntensity:.4}),group);
        const u=i/42;ring.position.copy(path[strand].getPoint(u));ring.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),path[strand].getTangent(u));
      }
    }
    if(index!==1)for(let i=0;i<=24;i++) {
      const a=path[0].getPoint(i/24),b=path[1].getPoint(i/24),mid=a.clone().add(b).multiplyScalar(.5);
      const r=index===3||index===5||index===9?.045:.08;
      rod(a,mid,r,mats[0],group);rod(mid,b,r,mats[1],group);
    }
    return group;
  }

  for(let i=0;i<10;i++)groups.push(build(i));
  let selected=0;
  return {
    render(index,phase) {
      selected=index;
      for(let i=0;i<groups.length;i++)groups[i].visible=i===index;
      const group=groups[index];group.rotation.set(phase,.035*Math.sin(phase),0);
      grid.visible=index===3;scan.visible=index===9;scan.position.set(Math.sin(phase)*12,0,3);
      if(index===8)group.traverse(item=>{
        const original=item.userData.original;if(!original)return;
        const values=item.geometry.attributes.position.array;
        for(let i=0;i<values.length;i+=3){const wave=1+.055*Math.sin(original[i]*1.3-phase*2);values[i+1]=original[i+1]*wave;values[i+2]=original[i+2]*wave;}
        item.geometry.attributes.position.needsUpdate=true;item.geometry.computeVertexNormals();
      });
      renderPass.camera=index===6?iso:camera;
      bloom.strength=0;
      composer.render();
    },
    resize(width,height){renderer.setSize(width,height,false);composer.setSize(width,height);},
    stats(){return {style:selected,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};}
  };
}
