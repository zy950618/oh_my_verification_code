/* negative_eval_only: browser code cannot issue a first-party business receipt. */
export function browserLikeHash(value) {
  let hash = 2166136261;
  for (const char of value) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return (hash >>> 0).toString(16);
}
