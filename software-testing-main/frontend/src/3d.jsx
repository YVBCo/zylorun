import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, PointMaterial, Points, Float } from '@react-three/drei';
import * as THREE from 'three';

export function HologramGlobe() {
  const points = useMemo(() => {
    const p = new Float32Array(3000);
    for (let i = 0; i < 3000; i++) {
      const x = (Math.random() - 0.5) * 3;
      const y = (Math.random() - 0.5) * 3;
      const z = (Math.random() - 0.5) * 3;
      p[i] = x; p[i+1] = y; p[i+2] = z;
    }
    return p;
  }, []);

  return (
    <div className="absolute inset-0 z-0 opacity-40 pointer-events-none">
      <Canvas camera={{ position: [0, 0, 5] }}>
        <ambientLight intensity={0.5} />
        <Float speed={1} rotationIntensity={0.5} floatIntensity={0.5}>
          <Sphere args={[1.5, 32, 32]}>
            <meshBasicMaterial color="#02040A" wireframe />
          </Sphere>
          <Points positions={points} stride={3}>
            <PointMaterial transparent color="#4DF3FF" size={0.02} sizeAttenuation={true} depthWrite={false} />
          </Points>
        </Float>
        <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.5} />
      </Canvas>
    </div>
  );
}
