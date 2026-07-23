import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BlogPostVoteControl } from "./BlogPostVoteControl";

describe("BlogPostVoteControl", () => {
  it("muestra los contadores de cada voto por separado", () => {
    render(<BlogPostVoteControl votesUp={5} votesDown={2} myVote={0} onVote={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Me ha resultado útil" })).toHaveTextContent("5");
    expect(screen.getByRole("button", { name: /no me ha resultado útil/i })).toHaveTextContent("2");
  });

  it("marca como pulsado el botón del voto actual", () => {
    render(<BlogPostVoteControl votesUp={1} votesDown={0} myVote={1} onVote={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Me ha resultado útil" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("llama a onVote con 1 o -1 al pulsar cada botón", async () => {
    const onVote = vi.fn();
    render(<BlogPostVoteControl votesUp={0} votesDown={0} myVote={0} onVote={onVote} />);

    await userEvent.click(screen.getByRole("button", { name: "Me ha resultado útil" }));
    expect(onVote).toHaveBeenCalledWith(1);

    await userEvent.click(screen.getByRole("button", { name: /no me ha resultado útil/i }));
    expect(onVote).toHaveBeenCalledWith(-1);
  });

  it("deshabilita ambos botones mientras se está votando", () => {
    render(<BlogPostVoteControl votesUp={0} votesDown={0} myVote={0} disabled onVote={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Me ha resultado útil" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /no me ha resultado útil/i })).toBeDisabled();
  });
});
