/** Chips con los avisos de una propuesta. */
import type { AdminSubmission } from "@/services/api/submissions";
import { submissionWarningLabels } from "../submission-form";

export function SubmissionWarnings({ submission }: { submission: AdminSubmission }) {
  const labels = submissionWarningLabels(submission);
  if (labels.length === 0) return null;
  return (
    <ul aria-label="Avisos" className="flex flex-wrap gap-1.5">
      {labels.map((label) => (
        <li
          key={label}
          className="font-mono text-[10px] uppercase tracking-wide border border-amber-400/50 text-amber-400 px-1.5 py-0.5 break-words"
        >
          {label}
        </li>
      ))}
    </ul>
  );
}
