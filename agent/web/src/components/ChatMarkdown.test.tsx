import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ChatMarkdown } from "./ChatMarkdown";
afterEach(cleanup);

it("met en forme la synthèse et ouvre chaque référence réelle d’une citation groupée", () => {
  const open = vi.fn();
  const { container } = render(<ChatMarkdown text={
    "Voici le projet :\n\n* **Objectif :** Installer les sangles [P1, P2].\n* **Points ouverts :**\n  * Valider les coutures.\n  * Définir la durée."
  } references={["P1", "P2"]} onReference={open} />);
  expect(container.querySelector("strong")?.textContent).toBe("Objectif :");
  expect(container.querySelectorAll("ul").length).toBe(2);
  expect(container.querySelectorAll("li").length).toBe(4);
  expect(container.textContent).not.toContain("**");
  fireEvent.click(screen.getByRole("button", { name: "Voir la source P2" }));
  expect(open).toHaveBeenCalledWith("P2");
});

it("garde le HTML, les liens actifs dangereux et les références inconnues en texte", () => {
  const { container } = render(<ChatMarkdown text={'<img src=x onerror=alert(1)>\n\n[ouvrir](javascript:alert(1)) [P99]\n\n```html\n<script>alert(1)</script>\n```'}
    references={["P1"]} onReference={vi.fn()} />);
  expect(container.querySelector("img, script, a, button")).toBeNull();
  expect(container.querySelector("pre code")?.textContent).toBe("<script>alert(1)</script>");
  expect(container.textContent).toContain("[P99]");
});
