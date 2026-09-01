import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AISuggestedActions } from "../components/ai-suggested-actions";
import { createActionPlanTask, generateAISuggestions } from "../lib/api";

vi.mock("../lib/api", () => ({
  ApiError: class ApiError extends Error {},
  createActionPlanTask: vi.fn(),
  generateAISuggestions: vi.fn(),
}));

const mockedGenerate = vi.mocked(generateAISuggestions);
const mockedCreate = vi.mocked(createActionPlanTask);

describe("AI suggested actions", () => {
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it("requires explicit generation and supports edit, add, and dismiss", async () => {
    mockedGenerate.mockResolvedValue({ status: "available", suggestions: [
      { title: "README düzenle", description: "Kurulum adımlarını ekle", reason: "Eksik README kanıtı", evidence_refs: ["signal:readme"] },
      { title: "İkinci öneri", description: "Açıklama", reason: "Kanıt", evidence_refs: ["signal:tests"] },
    ] });
    mockedCreate.mockResolvedValue({ id: "task-1", title: "Güncel başlık", description: "Kurulum adımlarını ekle", status: "todo", created_at: "", updated_at: "", completed_at: null });
    const user = userEvent.setup();
    render(<AISuggestedActions username="alice" />);
    expect(mockedGenerate).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Generate suggestions" }));
    expect(await screen.findByText("README düzenle")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    const title = screen.getByLabelText("Öneri başlığı");
    fireEvent.change(title, { target: { value: "Güncel başlık" } });
    await user.click(screen.getAllByRole("button", { name: "Add" })[0]);
    await waitFor(() => expect(mockedCreate).toHaveBeenCalledWith({ title: "Güncel başlık", description: "Kurulum adımlarını ekle" }));
    expect(screen.queryByText("Güncel başlık")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText("İkinci öneri")).not.toBeInTheDocument();
  });
});
