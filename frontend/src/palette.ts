// Categorical colours for topic clusters (Okabe and Ito palette, readable for
// the common forms of colour blindness). Cluster 0 is always the largest one.
export const CLUSTER_COLORS = [
  '#0072B2',
  '#E69F00',
  '#009E73',
  '#CC79A7',
  '#56B4E9',
  '#D55E00',
  '#8C7B00',
  '#6E6E6E',
]

export function clusterColor(cluster: number): string {
  return CLUSTER_COLORS[((cluster % CLUSTER_COLORS.length) + CLUSTER_COLORS.length) % CLUSTER_COLORS.length]
}

export const SEED_COLOR = '#1f2937'
