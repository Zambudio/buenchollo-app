import { Link } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { CheckCircle2 } from "lucide-react";

interface SubmissionSuccessProps {
  onPublishAnother: () => void;
}

export function SubmissionSuccess({ onPublishAnother }: SubmissionSuccessProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <div className="border border-surface-700 bg-surface-800 p-6 sm:p-8 text-center space-y-5">
      <CheckCircle2 className="size-12 mx-auto text-cyan-glow" aria-hidden="true" />
      <h2 ref={headingRef} tabIndex={-1} className="text-2xl font-bold tracking-tight outline-none">
        ¡Gracias! Revisaremos tu chollo y te avisaremos por email.
      </h2>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Link
          to="/mis-chollos"
          className="inline-flex items-center justify-center bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-6 py-3 hover:bg-foreground transition-colors"
        >
          Ver mis chollos
        </Link>
        <button
          type="button"
          onClick={onPublishAnother}
          className="inline-flex items-center justify-center border border-surface-600 bg-surface-900 font-mono text-xs font-bold px-6 py-3 hover:border-cyan-glow transition-colors"
        >
          Publicar otro
        </button>
      </div>
    </div>
  );
}
