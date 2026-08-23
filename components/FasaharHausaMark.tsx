import React from 'react';

/** Small geometric seal for the "Fasahar Hausa" header mark — an octagon
 *  frame (same 8-point geometry as ArewaLogo, "8 speakers · Arewa
 *  geometry") around a diamond lattice, the interlocking-diamond motif
 *  common across Hausa textile and architectural ornamentation (e.g. the
 *  geometric relief work on Kano's traditional mud buildings). A minted
 *  seal, not literal "FH" initials — those would read as generic
 *  corporate monogram, not Hausa geometry. */
export const FasaharHausaMark: React.FC<{ size?: number; className?: string }> = ({ size = 20, className = '' }) => (
  <svg viewBox="0 0 100 100" width={size} height={size} className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
    <polygon
      points="90.6,66.9 66.9,90.6 33.1,90.6 9.4,66.9 9.4,33.1 33.1,9.4 66.9,9.4 90.6,33.1"
      stroke="currentColor"
      strokeWidth="4.5"
      strokeLinejoin="round"
    />
    <polygon
      points="50,26 74,50 50,74 26,50"
      stroke="currentColor"
      strokeWidth="4.5"
      strokeLinejoin="round"
    />
    <polygon points="50,40 60,50 50,60 40,50" fill="currentColor" />
  </svg>
);
