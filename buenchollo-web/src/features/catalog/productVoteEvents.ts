export const PRODUCT_VOTE_EVENT = "bct:product-vote";

export function publishProductVote(productId: string, voted: boolean, source: "card" | "top") {
  window.dispatchEvent(
    new CustomEvent(PRODUCT_VOTE_EVENT, { detail: { productId, voted, source } }),
  );
}

export type VoteChange = { productId: string; voted: boolean; source: "card" | "top" };
