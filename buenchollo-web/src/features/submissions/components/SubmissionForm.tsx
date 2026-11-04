import { useCallback, useMemo, useState, type ReactNode } from "react";
import { useForm, type FieldPath } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { ApiError } from "@/services/api/client";
import {
  isProfileIncompleteError,
  isSubmissionDuplicateError,
  submissionsApi,
  type LinkCheckResult,
  type LinkCheckStatus,
} from "@/services/api/submissions";
import {
  computeDiscount,
  parsePrice,
  submissionFormSchema,
  toSubmissionPayload,
  type SubmissionFormValues,
} from "@/lib/validation/submissions";
import { toDatetimeLocal } from "@/lib/format";
import { loginSearch } from "@/lib/safe-redirect";
import { useCategoryOptions } from "../hooks/useCategoryOptions";
import { ImageUploader, type ImageUploaderState } from "./ImageUploader";
import { SubmissionPreviewCard } from "./SubmissionPreviewCard";
import { SubmissionSuccess } from "./SubmissionSuccess";

interface SubmissionFormProps {
  url: string;
  result: LinkCheckResult;
  /** 409 SUBMISSION_DUPLICATE: vuelve al paso 1 con el estado recibido. */
  onDuplicate: (result: LinkCheckResult) => void;
  onBack: () => void;
  onPublishAnother: () => void;
  onProfileIncomplete?: () => void;
}

const DESCRIPTION_MAX = 10_000;

type FieldName = FieldPath<SubmissionFormValues>;
const FIELD_NAMES = new Set<string>([
  "title",
  "description",
  "current_price",
  "previous_price",
  "coupon_code",
  "shipping_info",
  "store_name",
  "category_id",
  "subcategory_id",
  "starts_at",
  "expires_at",
]);

/** 49.9 → "49,90"; 99 → "99" (formato de entrada es-ES). */
function priceInput(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value <= 0) return "";
  return (Number.isInteger(value) ? String(value) : value.toFixed(2)).replace(".", ",");
}

function initialValues(result: LinkCheckResult): SubmissionFormValues {
  const p = result.prefill;
  return {
    title: (p?.title ?? "").slice(0, 200),
    description: p?.description ?? "",
    current_price: priceInput(p?.current_price),
    previous_price: priceInput(p?.previous_price),
    coupon_code: "",
    shipping_info: "",
    store_name: "",
    category_id: "",
    subcategory_id: "",
    starts_at: "",
    expires_at: toDatetimeLocal(p?.expires_at),
    images: [],
    image_url: "",
  };
}

function initialImages(result: LinkCheckResult): string[] {
  const p = result.prefill;
  if (!p) return [];
  return p.images.length ? p.images : p.image_url ? [p.image_url] : [];
}

const cleanPydanticMessage = (msg: string) => msg.replace(/^Value error, /, "");

const inputCls =
  "w-full min-w-0 bg-surface-900 border border-surface-700 px-3 py-2.5 text-base sm:text-sm text-foreground outline-none focus:border-cyan-glow aria-[invalid=true]:border-alert-red read-only:text-muted-foreground read-only:focus:border-surface-700";

interface FieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: ReactNode;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

function Field({ id, label, error, hint, required, children, className = "" }: FieldProps) {
  return (
    <div className={`min-w-0 ${className}`}>
      <label htmlFor={id} className="block text-xs font-mono uppercase text-muted-foreground mb-1">
        {label}
        {required && (
          <span className="text-cyan-glow" aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="mt-1 text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1 text-xs text-alert-red">
          {error}
        </p>
      )}
    </div>
  );
}

const describedBy = (id: string, error?: string, hint?: boolean) =>
  error ? `${id}-error` : hint ? `${id}-hint` : undefined;

export function SubmissionForm({
  url,
  result,
  onDuplicate,
  onBack,
  onPublishAnother,
  onProfileIncomplete,
}: SubmissionFormProps) {
  const nav = useNavigate();
  const {
    cats,
    subcats,
    isLoading: catsLoading,
    isError: catsError,
    refetch,
  } = useCategoryOptions();
  const [uploads, setUploads] = useState<ImageUploaderState>({
    images: [],
    cover: null,
    isUploading: false,
    hasErrors: false,
  });
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const prefillImages = useMemo(() => initialImages(result), [result]);
  const detectedStore = result.store_name?.trim() || null;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    setFocus,
    formState: { errors },
  } = useForm<SubmissionFormValues>({
    resolver: zodResolver(submissionFormSchema),
    defaultValues: initialValues(result),
    mode: "onTouched",
  });

  const onImagesChange = useCallback(
    (state: ImageUploaderState) => {
      setUploads(state);
      setValue("images", state.images);
      setValue("image_url", state.cover ?? "");
    },
    [setValue],
  );

  const mutation = useMutation({
    mutationFn: (values: SubmissionFormValues) =>
      submissionsApi.create(toSubmissionPayload(values, url)),
    onSuccess: () => setSubmitted(true),
    onError: (error) => {
      if (isSubmissionDuplicateError(error)) {
        const data = error.data ?? {};
        onDuplicate({
          ...result,
          status: (data.reason as LinkCheckStatus | undefined) ?? "in_review",
          previously_published: false,
          existing_deal: (data.existing_deal as LinkCheckResult["existing_deal"]) ?? null,
        });
        return;
      }
      if (error instanceof ApiError && error.status === 401) {
        void nav({
          to: "/login",
          search: loginSearch(`/publicar?url=${encodeURIComponent(url)}`),
        });
        return;
      }
      if (isProfileIncompleteError(error)) {
        onProfileIncomplete?.();
        return;
      }
      if (error instanceof ApiError && error.status === 422) {
        const rawDetail = error.data?.detail;
        const detail = Array.isArray(rawDetail)
          ? (rawDetail as { loc?: unknown[]; msg?: string }[])
          : [];
        const general: string[] = [];
        let first: FieldName | null = null;
        for (const d of detail) {
          const field = d.loc?.[0] === "body" ? d.loc[1] : undefined;
          const message = cleanPydanticMessage(d.msg ?? "Valor no válido");
          if (typeof field === "string" && FIELD_NAMES.has(field)) {
            setError(field as FieldName, { type: "server", message });
            first ??= field as FieldName;
          } else {
            general.push(message);
          }
        }
        if (first) setFocus(first);
        setSubmitError(
          general.length ? general.join(" · ") : first ? null : "Revisa los datos del formulario.",
        );
        return;
      }
      if (error instanceof ApiError && (error.status === 429 || error.status === 400)) {
        setSubmitError(error.message);
        return;
      }
      setSubmitError("No se pudo enviar el chollo. Inténtalo de nuevo.");
    },
  });

  const onValid = (values: SubmissionFormValues) => {
    setSubmitError(null);
    mutation.mutate(values);
  };

  const [title, currentRaw, previousRaw, categoryId, description, typedStore] = watch([
    "title",
    "current_price",
    "previous_price",
    "category_id",
    "description",
    "store_name",
  ]);
  const current = parsePrice(currentRaw);
  const previous = parsePrice(previousRaw);
  const currentNum = Number.isFinite(current) && current > 0 ? current : null;
  const previousNum = Number.isFinite(previous) && previous > 0 ? previous : null;
  const discount = computeDiscount(currentNum, previousNum);
  const filteredSubcats = subcats.filter((s) => s.parent_id === categoryId);

  if (submitted) return <SubmissionSuccess onPublishAnother={onPublishAnother} />;

  const blockedReason = uploads.isUploading
    ? "Espera a que terminen de subirse las imágenes."
    : uploads.hasErrors
      ? "Quita las imágenes con error antes de enviar."
      : null;
  const e = errors;

  return (
    <form
      onSubmit={handleSubmit(onValid)}
      noValidate
      aria-label="Datos del chollo"
      className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,360px)]"
    >
      <div className="min-w-0 space-y-5">
        <div className="flex items-center gap-3 border border-surface-700 bg-surface-800 px-3 py-2">
          <span
            className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground"
            title={url}
          >
            {url}
          </span>
          <button
            type="button"
            onClick={onBack}
            className="inline-flex shrink-0 items-center gap-1 font-mono text-xs font-bold text-cyan-glow hover:underline"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Cambiar enlace
          </button>
        </div>

        {result.is_amazon && !result.prefill && (
          <p
            role="status"
            className="border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300"
          >
            No hemos podido leer los datos de Amazon. Rellena el formulario a mano.
          </p>
        )}

        <Field id="sub-title" label="Título" required error={e.title?.message}>
          <input
            id="sub-title"
            type="text"
            maxLength={200}
            autoComplete="off"
            aria-invalid={e.title ? true : undefined}
            aria-describedby={describedBy("sub-title", e.title?.message)}
            aria-required="true"
            className={inputCls}
            {...register("title")}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field id="sub-price" label="Precio (€)" required error={e.current_price?.message}>
            <input
              id="sub-price"
              type="text"
              inputMode="decimal"
              autoComplete="off"
              placeholder="49,99"
              aria-invalid={e.current_price ? true : undefined}
              aria-describedby={describedBy("sub-price", e.current_price?.message)}
              aria-required="true"
              className={`${inputCls} font-mono`}
              {...register("current_price")}
            />
          </Field>
          <Field
            id="sub-prev-price"
            label="Precio anterior (€)"
            error={e.previous_price?.message}
            hint={discount ? undefined : "Opcional"}
          >
            <div className="relative">
              <input
                id="sub-prev-price"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                placeholder="79,99"
                aria-invalid={e.previous_price ? true : undefined}
                aria-describedby={
                  [
                    describedBy("sub-prev-price", e.previous_price?.message, !discount),
                    discount ? "sub-discount" : undefined,
                  ]
                    .filter(Boolean)
                    .join(" ") || undefined
                }
                className={`${inputCls} font-mono ${discount ? "pr-16" : ""}`}
                {...register("previous_price")}
              />
              {discount != null && discount > 0 && (
                <span
                  aria-hidden="true"
                  data-testid="discount-badge"
                  className="badge-discount absolute right-2 top-1/2 -translate-y-1/2"
                >
                  -{discount}%
                </span>
              )}
              {/* Región viva siempre montada: solo cambia su texto. */}
              <span id="sub-discount" aria-live="polite" className="sr-only">
                {discount ? `Descuento del ${discount}%` : ""}
              </span>
            </div>
          </Field>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            id="sub-coupon"
            label="Código de descuento"
            error={e.coupon_code?.message}
            hint="Opcional"
          >
            <input
              id="sub-coupon"
              type="text"
              maxLength={64}
              autoComplete="off"
              autoCapitalize="characters"
              aria-invalid={e.coupon_code ? true : undefined}
              aria-describedby={describedBy("sub-coupon", e.coupon_code?.message, true)}
              className={`${inputCls} font-mono`}
              {...register("coupon_code")}
            />
          </Field>
          <Field
            id="sub-shipping"
            label="Gastos de envío"
            error={e.shipping_info?.message}
            hint="Ej.: Gratis, 3,99 € o gratis con Prime"
          >
            <input
              id="sub-shipping"
              type="text"
              maxLength={120}
              autoComplete="off"
              aria-invalid={e.shipping_info ? true : undefined}
              aria-describedby={describedBy("sub-shipping", e.shipping_info?.message, true)}
              className={inputCls}
              {...register("shipping_info")}
            />
          </Field>
        </div>

        {detectedStore ? (
          <Field id="sub-store" label="Tienda" hint="Detectada a partir del enlace">
            <input
              id="sub-store"
              type="text"
              readOnly
              value={detectedStore}
              aria-describedby="sub-store-hint"
              className={inputCls}
            />
          </Field>
        ) : (
          <Field
            id="sub-store"
            label="Tienda"
            error={e.store_name?.message}
            hint="No la hemos reconocido: escribe su nombre"
          >
            <input
              id="sub-store"
              type="text"
              maxLength={80}
              autoComplete="off"
              aria-invalid={e.store_name ? true : undefined}
              aria-describedby={describedBy("sub-store", e.store_name?.message, true)}
              className={inputCls}
              {...register("store_name")}
            />
          </Field>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="sub-category" label="Categoría" required error={e.category_id?.message}>
            <select
              id="sub-category"
              disabled={catsLoading}
              aria-invalid={e.category_id ? true : undefined}
              aria-describedby={describedBy("sub-category", e.category_id?.message)}
              aria-required="true"
              className={inputCls}
              {...register("category_id", {
                onChange: () => setValue("subcategory_id", ""),
              })}
            >
              <option value="">{catsLoading ? "Cargando…" : "— Elige categoría —"}</option>
              {cats.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {catsError && (
              <p className="mt-1 text-xs text-alert-red">
                No se pudieron cargar las categorías.{" "}
                <button type="button" onClick={() => void refetch()} className="underline">
                  Reintentar
                </button>
              </p>
            )}
          </Field>
          <Field id="sub-subcategory" label="Subcategoría" error={e.subcategory_id?.message}>
            <select
              id="sub-subcategory"
              disabled={!categoryId || filteredSubcats.length === 0}
              aria-invalid={e.subcategory_id ? true : undefined}
              aria-describedby={describedBy("sub-subcategory", e.subcategory_id?.message)}
              className={inputCls}
              {...register("subcategory_id")}
            >
              <option value="">
                {categoryId
                  ? filteredSubcats.length
                    ? "— Opcional —"
                    : "Sin subcategorías"
                  : "Elige categoría primero"}
              </option>
              {filteredSubcats.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="sub-starts" label="Empieza" error={e.starts_at?.message} hint="Opcional">
            <input
              id="sub-starts"
              type="datetime-local"
              aria-invalid={e.starts_at ? true : undefined}
              aria-describedby={describedBy("sub-starts", e.starts_at?.message, true)}
              className={inputCls}
              {...register("starts_at")}
            />
          </Field>
          <Field id="sub-expires" label="Termina" error={e.expires_at?.message} hint="Opcional">
            <input
              id="sub-expires"
              type="datetime-local"
              aria-invalid={e.expires_at ? true : undefined}
              aria-describedby={describedBy("sub-expires", e.expires_at?.message, true)}
              className={inputCls}
              {...register("expires_at")}
            />
          </Field>
        </div>

        <Field
          id="sub-description"
          label="Descripción"
          error={e.description?.message}
          hint={
            <span className="flex justify-between gap-2">
              <span>Cuenta por qué es un buen chollo</span>
              <span
                className={`tabular-nums ${description.length > DESCRIPTION_MAX ? "text-alert-red" : ""}`}
              >
                {description.length.toLocaleString("es-ES")}/
                {DESCRIPTION_MAX.toLocaleString("es-ES")}
              </span>
            </span>
          }
        >
          <textarea
            id="sub-description"
            rows={6}
            aria-invalid={e.description ? true : undefined}
            aria-describedby={describedBy("sub-description", e.description?.message, true)}
            className={`${inputCls} resize-y`}
            {...register("description")}
          />
        </Field>

        <ImageUploader initial={prefillImages} onChange={onImagesChange} />
      </div>

      <aside className="min-w-0 space-y-4 lg:sticky lg:top-24 lg:self-start">
        <h2 className="text-xs font-mono uppercase text-muted-foreground">Vista previa</h2>
        <SubmissionPreviewCard
          title={title}
          currentPrice={currentNum}
          previousPrice={previousNum}
          images={uploads.images}
          storeName={detectedStore ?? typedStore}
        />

        {submitError && (
          <p role="alert" className="border border-alert-red/60 bg-alert-red/10 p-3 text-sm">
            {submitError}
          </p>
        )}

        <button
          type="submit"
          disabled={Boolean(blockedReason) || mutation.isPending}
          aria-describedby={blockedReason ? "sub-blocked" : undefined}
          className="w-full inline-flex items-center justify-center gap-2 bg-cyan-glow text-surface-900 font-mono text-sm font-bold px-6 py-3.5 hover:bg-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="size-4" aria-hidden="true" />
          )}
          {mutation.isPending ? "Enviando…" : "Enviar chollo"}
        </button>
        {blockedReason && (
          <p id="sub-blocked" className="text-xs text-muted-foreground text-center">
            {blockedReason}
          </p>
        )}
        <p className="text-xs text-muted-foreground text-center">
          Lo revisaremos antes de publicarlo.
        </p>
      </aside>
    </form>
  );
}
