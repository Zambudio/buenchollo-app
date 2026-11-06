/**
 * Estado compartido de los votos del usuario a productos del top.
 *
 * Tarjetas, ficha y top leen el mismo estado: un voto en cualquiera se refleja
 * en los demás sin peticiones extra. Las consultas de estado se agrupan en
 * lotes para que un listado de tarjetas haga una sola petición.
 */
import { useEffect, useState, useSyncExternalStore } from "react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { errorMessage } from "@/lib/errors";
import { catalogService } from "@/services/api/catalog";

// Debe coincidir con MAX_VOTE_LOOKUP del endpoint /catalog/my-votes.
const LOOKUP_BATCH_SIZE = 50;

export type ProductVoteChange = { productId: string; voted: boolean };

let owner: string | null = null;
const votes = new Map<string, boolean>();
const requested = new Set<string>();
let queue: string[] = [];
let flushScheduled = false;
const listeners = new Set<() => void>();
const changeListeners = new Set<(change: ProductVoteChange) => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function setOwner(userId: string | null) {
  if (owner === userId) return;
  owner = userId;
  votes.clear();
  requested.clear();
  queue = [];
  emit();
}

async function flush() {
  flushScheduled = false;
  const ids = queue;
  const forUser = owner;
  queue = [];
  for (let start = 0; start < ids.length; start += LOOKUP_BATCH_SIZE) {
    const batch = ids.slice(start, start + LOOKUP_BATCH_SIZE);
    try {
      const voted = new Set(await catalogService.myVotes(batch));
      if (owner !== forUser) return;
      // Un voto emitido mientras la consulta estaba en curso es más reciente.
      batch.forEach((id) => {
        if (!votes.has(id)) votes.set(id, voted.has(id));
      });
      emit();
    } catch {
      // Sin estado previo el botón sigue utilizable; se reintenta en el próximo montaje.
      batch.forEach((id) => requested.delete(id));
    }
  }
}

function requestVotes(ids: string[], userId: string | null) {
  setOwner(userId);
  if (!userId) return;
  for (const id of ids) {
    if (requested.has(id)) continue;
    requested.add(id);
    queue.push(id);
  }
  if (queue.length && !flushScheduled) {
    flushScheduled = true;
    setTimeout(() => void flush(), 0);
  }
}

/** Avisa de cada voto confirmado por la API (para refrescar rankings). */
export function onProductVoteChange(listener: (change: ProductVoteChange) => void) {
  changeListeners.add(listener);
  return () => {
    changeListeners.delete(listener);
  };
}

/** Solo para tests: el estado vive a nivel de módulo. */
export function resetProductVotes() {
  setOwner(null);
  changeListeners.clear();
}

export function useProductVote(productId: string) {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [pending, setPending] = useState(false);

  useEffect(() => requestVotes([productId], userId), [productId, userId]);

  const voted = useSyncExternalStore(
    subscribe,
    () => userId !== null && owner === userId && votes.get(productId) === true,
    () => false,
  );

  const toggle = async () => {
    if (pending || !userId) return;
    setPending(true);
    try {
      const result = await catalogService.vote(productId);
      if (owner === userId) {
        votes.set(productId, result.voted);
        emit();
      }
      changeListeners.forEach((listener) => listener({ productId, voted: result.voted }));
      toast.success(result.voted ? "Producto votado para el top" : "Voto al producto retirado");
    } catch (error) {
      toast.error(errorMessage(error, "No hemos podido registrar tu voto. Inténtalo de nuevo."));
    } finally {
      setPending(false);
    }
  };

  return { isLoggedIn: userId !== null, voted, pending, toggle };
}
