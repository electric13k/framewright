// The series cast: one locked look per character, used by every episode and every way they are drawn
// (3D figure, phone avatar, cut-out). Episodes change pose and light only, never these values.
// head: 'blank' (plain bone circle, default) | 'helmet' (visor, no face) | 'mask' (plain plate, no features).
// Give every character ONE recognition item (scarf, cap, bag, apron...) in a colour no one else wears.
export const INK = '#0b0f14', BONE = '#f1eee9';
export const CAST = {
  hero: { head: 'blank', top: '#1d2733', sleeve: '#1d2733', legs: '#2a3a5c', scarf: '#fd8358' },
  mother: { head: 'blank', hair: '#3a2a22', top: '#7a3b32', skirt: '#2e3946', apron: '#d8cfc0', legs: INK },
  courier: { head: 'helmet', helmet: '#e5484d', top: '#2b2f36', legs: '#1a1d22', bag: '#e5484d' },
  stranger: { head: 'mask', mask: '#c9c2b6', top: '#14181d', legs: INK, cap: '#14181d' },
};
