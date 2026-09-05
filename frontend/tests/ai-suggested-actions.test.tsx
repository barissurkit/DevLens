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

  it("ignores a late response after workspace identity changes", async () => {
    let resolve: (value: { status: "available"; suggestions: [] }) => void = () => undefined;
    mockedGenerate.mockReturnValue(new Promise((complete) => { resolve = complete; }));
    const user = userEvent.setup();
    const { rerender } = render(<AISuggestedActions key="alice" username="alice" />);
    await user.click(screen.getByRole("button", { name: "Generate suggestions" }));
    rerender(<AISuggestedActions key="bob" username="bob" />);
    resolve({ status: "available", suggestions: [] });
    await waitFor(() => expect(screen.getByRole("button", { name: "Generate suggestions" })).toBeInTheDocument());
    expect(screen.queryByText("AI önerileri şu anda kullanılamıyor.")).not.toBeInTheDocument();
  });

  it("ignores a late error after the suggestion component unmounts", async () => {
    let reject: (reason: Error) => void = () => undefined;
    mockedGenerate.mockReturnValue(new Promise((_, fail) => { reject = fail; }));
    const user = userEvent.setup();
    const { unmount } = render(<AISuggestedActions username="alice" />);
    await user.click(screen.getByRole("button", { name: "Generate suggestions" }));
    unmount();
    reject(new Error("late failure"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("preserves previous suggestions when a later generation fails", async () => {
    mockedGenerate
      .mockResolvedValueOnce({ status: "available", suggestions: [{ title: "İlk öneri", description: "Açıklama", reason: "Kanıt", evidence_refs: ["signal:readme"] }] })
      .mockRejectedValueOnce(new Error("temporary failure"));
    const user = userEvent.setup();
    render(<AISuggestedActions username="alice" />);
    await user.click(screen.getByRole("button", { name: "Generate suggestions" }));
    expect(await screen.findByText("İlk öneri")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yeniden oluştur" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText("İlk öneri")).toBeInTheDocument();
  });

  it("clears previous suggestions for a valid empty result", async () => {
    mockedGenerate
      .mockResolvedValueOnce({ status: "available", suggestions: [{ title: "İlk öneri", description: "Açıklama", reason: "Kanıt", evidence_refs: ["signal:readme"] }] })
      .mockResolvedValueOnce({ status: "available", suggestions: [] });
    const user = userEvent.setup();
    render(<AISuggestedActions username="alice" />);
    await user.click(screen.getByRole("button", { name: "Generate suggestions" }));
    expect(await screen.findByText("İlk öneri")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Yeniden oluştur" }));
    await waitFor(() => expect(screen.queryByText("İlk öneri")).not.toBeInTheDocument());
    expect(screen.getByText("Bu analiz için temellendirilebilir öneri bulunamadı.")).toBeInTheDocument();
  });
});
