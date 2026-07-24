export function sumWeights(weights: { weight: number }[]) {
  return weights.reduce((total, row) => total + row.weight, 0);
}

export function boundsAreFeasible(assetCount: number, minimum: number, maximum: number) {
  return assetCount >= 2 && minimum * assetCount <= 1 && maximum * assetCount >= 1;
}
