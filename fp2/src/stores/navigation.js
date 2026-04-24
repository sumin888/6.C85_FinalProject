import { writable, derived } from 'svelte/store';

export const FEATURED = [
  'Dorchester', 'Roxbury', 'Mission Hill',
  'East Boston', 'Hyde Park', 'South End',
];

export const currentIndex = writable(0);
export const currentNeighborhood = derived(currentIndex, $i => FEATURED[$i]);
export const deepDiveStep = writable(0);

export function nextNeighborhood() {
  currentIndex.update(i => (i + 1) % FEATURED.length);
  deepDiveStep.set(0);
}

export function prevNeighborhood() {
  currentIndex.update(i => (i - 1 + FEATURED.length) % FEATURED.length);
  deepDiveStep.set(0);
}

export function goToNeighborhood(name) {
  const idx = FEATURED.indexOf(name);
  if (idx >= 0) {
    currentIndex.set(idx);
    deepDiveStep.set(0);
  }
}
