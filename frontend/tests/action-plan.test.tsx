import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ActionPlan } from "../components/action-plan";
import { useAuth } from "../components/auth-provider";
import { createActionPlanTask, deleteActionPlanTask, getActionPlan, updateActionPlanTask } from "../lib/api";
import type { ActionPlanTask, AuthenticatedUser } from "../lib/types";

vi.mock("../components/auth-provider", () => ({ useAuth: vi.fn() }));
vi.mock("../lib/api", () => ({
  ApiError: class ApiError extends Error {},
  createActionPlanTask: vi.fn(),
  deleteActionPlanTask: vi.fn(),
  getActionPlan: vi.fn(),
  updateActionPlanTask: vi.fn(),
}));

const mockedAuth = vi.mocked(useAuth);
const mockedGet = vi.mocked(getActionPlan);
const mockedCreate = vi.mocked(createActionPlanTask);
const mockedUpdate = vi.mocked(updateActionPlanTask);
const mockedDelete = vi.mocked(deleteActionPlanTask);

const user: AuthenticatedUser = { github_login: "alice", display_name: "Alice", avatar_url: null, github_html_url: null };
const task: ActionPlanTask = { id: "task-1", title: "README geliştir", description: "Kullanım ekle", status: "todo", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", completed_at: null };

describe("Action Plan workspace UI", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    vi.clearAllMocks();
    mockedAuth.mockReturnValue({ status: "authenticated", user, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    mockedGet.mockResolvedValue({ tasks: [] });
  });

  it("is hidden for anonymous users and loads an empty authenticated workspace", async () => {
    mockedAuth.mockReturnValue({ status: "anonymous", user: null, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    const { rerender } = render(<ActionPlan />);
    expect(screen.queryByRole("heading", { name: "Action Plan" })).not.toBeInTheDocument();
    mockedAuth.mockReturnValue({ status: "authenticated", user, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    rerender(<ActionPlan />);
    expect(await screen.findByText("Henüz görev yok.")).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledOnce();
  });

  it("creates, edits, changes status, and deletes from successful server responses", async () => {
    mockedGet.mockResolvedValue({ tasks: [task] });
    mockedCreate.mockResolvedValue({ ...task, id: "task-2", title: "Yeni görev" });
    mockedUpdate.mockResolvedValue({ ...task, title: "Güncel görev", description: "Güncel açıklama", status: "done", completed_at: "2026-01-02T00:00:00Z" });
    mockedDelete.mockResolvedValue(undefined);
    const userActions = userEvent.setup();
    render(<ActionPlan />);
    expect(await screen.findByDisplayValue("README geliştir")).toBeInTheDocument();
    await userActions.type(screen.getByLabelText("Yeni görev"), "Yeni görev");
    await userActions.type(screen.getByPlaceholderText("Açıklama (isteğe bağlı)"), "Kullanım ekle");
    await userActions.click(screen.getByRole("button", { name: "Görev ekle" }));
    await waitFor(() => expect(mockedCreate).toHaveBeenCalledWith({ title: "Yeni görev", description: "Kullanım ekle" }));
    expect(screen.getByLabelText("Yeni görev")).toHaveValue("");
    expect(screen.getByPlaceholderText("Açıklama (isteğe bağlı)")).toHaveValue("");
    expect(screen.getAllByDisplayValue("Yeni görev")).toHaveLength(1);
    const titleInput = screen.getByDisplayValue("README geliştir");
    await userActions.clear(titleInput);
    await userActions.type(titleInput, "Güncel görev");
    await userActions.tab();
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledWith("task-1", { title: "Güncel görev" }));
    await userActions.selectOptions(screen.getAllByLabelText("Görev durumu")[1], "done");
    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledWith("task-1", { status: "done" }));
    await userActions.click(screen.getAllByRole("button", { name: "Sil" })[1]);
    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith("task-1"));
  });

  it("keeps a successful create visible when the initial load resolves with a stale snapshot", async () => {
    let resolveLoad: (result: { tasks: ActionPlanTask[] }) => void = () => undefined;
    mockedGet.mockReturnValue(new Promise((resolve) => { resolveLoad = resolve; }));
    const createdTask: ActionPlanTask = { ...task, id: "task-2", title: "README kullanımını geliştir", description: "Kurulum adımlarını ekle" };
    mockedCreate.mockResolvedValue(createdTask);
    const userActions = userEvent.setup();
    render(<ActionPlan />);

    await userActions.type(screen.getByLabelText("Yeni görev"), createdTask.title);
    await userActions.type(screen.getByLabelText("Görev açıklaması"), createdTask.description ?? "");
    await userActions.click(screen.getByRole("button", { name: "Görev ekle" }));
    await waitFor(() => expect(mockedCreate).toHaveBeenCalled());
    expect(screen.getByLabelText("Yeni görev")).toHaveValue("");
    expect(screen.getByLabelText("Görev açıklaması")).toHaveValue("");

    resolveLoad({ tasks: [] });
    expect(await screen.findByDisplayValue(createdTask.title)).toBeInTheDocument();
    expect(screen.getAllByDisplayValue(createdTask.title)).toHaveLength(1);
  });

  it("keeps a suggested task when the initial load resolves with a stale snapshot", async () => {
    let resolveLoad: (result: { tasks: ActionPlanTask[] }) => void = () => undefined;
    mockedGet.mockReturnValue(new Promise((resolve) => { resolveLoad = resolve; }));
    render(<ActionPlan />);
    window.dispatchEvent(new CustomEvent<ActionPlanTask>("devlens:suggested-task-added", { detail: { ...task, id: "suggested-1", title: "AI görevi" } }));
    resolveLoad({ tasks: [] });
    expect(await screen.findByDisplayValue("AI görevi")).toBeInTheDocument();
  });

  it("uses the later server version when a GET contains the created task ID", async () => {
    let resolveLoad: (result: { tasks: ActionPlanTask[] }) => void = () => undefined;
    mockedGet.mockReturnValue(new Promise((resolve) => { resolveLoad = resolve; }));
    const createdTask: ActionPlanTask = { ...task, id: "task-2", title: "İlk başlık" };
    mockedCreate.mockResolvedValue(createdTask);
    const userActions = userEvent.setup();
    render(<ActionPlan />);

    await userActions.type(screen.getByLabelText("Yeni görev"), createdTask.title);
    await userActions.click(screen.getByRole("button", { name: "Görev ekle" }));
    await waitFor(() => expect(mockedCreate).toHaveBeenCalled());
    resolveLoad({ tasks: [{ ...createdTask, title: "Sunucudaki başlık" }] });

    expect(await screen.findByDisplayValue("Sunucudaki başlık")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("İlk başlık")).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Görev başlığı")).toHaveLength(1);
  });

  it("keeps private state isolated and reports failed mutations", async () => {
    mockedGet.mockResolvedValue({ tasks: [task] });
    mockedCreate.mockRejectedValue(new Error("failed"));
    const userActions = userEvent.setup();
    const { rerender } = render(<ActionPlan />);
    expect(await screen.findByDisplayValue("README geliştir")).toBeInTheDocument();
    mockedAuth.mockReturnValue({ status: "authenticated", user: { ...user }, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    rerender(<ActionPlan />);
    expect(screen.getByDisplayValue("README geliştir")).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledOnce();
    await userActions.type(screen.getByLabelText("Yeni görev"), "Başarısız");
    await userActions.type(screen.getByPlaceholderText("Açıklama (isteğe bağlı)"), "Daha sonra tekrar dene");
    await userActions.click(screen.getByRole("button", { name: "Görev ekle" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Görev oluşturulamadı.");
    expect(screen.getByLabelText("Yeni görev")).toHaveValue("Başarısız");
    expect(screen.getByPlaceholderText("Açıklama (isteğe bağlı)")).toHaveValue("Daha sonra tekrar dene");
    mockedAuth.mockReturnValue({ status: "authenticated", user: { ...user, github_login: "bob" }, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    mockedGet.mockResolvedValue({ tasks: [] });
    rerender(<ActionPlan />);
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Henüz görev yok.")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("README geliştir")).not.toBeInTheDocument();
  });

  it("rejects late responses from the previous user", async () => {
    let resolveUserAGet: (result: { tasks: ActionPlanTask[] }) => void = () => undefined;
    let resolveUserACreate: (result: ActionPlanTask) => void = () => undefined;
    mockedGet
      .mockReturnValueOnce(new Promise((resolve) => { resolveUserAGet = resolve; }))
      .mockResolvedValueOnce({ tasks: [] });
    mockedCreate.mockReturnValue(new Promise((resolve) => { resolveUserACreate = resolve; }));
    const userActions = userEvent.setup();
    const { rerender } = render(<ActionPlan />);

    await userActions.type(screen.getByLabelText("Yeni görev"), "A özel görev");
    await userActions.click(screen.getByRole("button", { name: "Görev ekle" }));
    mockedAuth.mockReturnValue({ status: "authenticated", user: { ...user, github_login: "bob" }, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    rerender(<ActionPlan />);

    resolveUserAGet({ tasks: [task] });
    resolveUserACreate({ ...task, title: "A özel görev" });
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Henüz görev yok.")).toBeInTheDocument();
    expect(screen.queryAllByLabelText("Görev başlığı")).toHaveLength(0);
  });

  it("does not apply a late create error to the next user", async () => {
    let rejectUserACreate: (reason: Error) => void = () => undefined;
    mockedGet.mockResolvedValue({ tasks: [] });
    mockedCreate.mockReturnValue(new Promise((_, reject) => { rejectUserACreate = reject; }));
    const userActions = userEvent.setup();
    const { rerender } = render(<ActionPlan />);

    await userActions.type(screen.getByLabelText("Yeni görev"), "A başarısız görev");
    await userActions.click(screen.getByRole("button", { name: "Görev ekle" }));
    mockedAuth.mockReturnValue({ status: "authenticated", user: { ...user, github_login: "bob" }, errorMessage: null, refresh: vi.fn(), logout: vi.fn() });
    rerender(<ActionPlan />);

    rejectUserACreate(new Error("A create failed"));
    await waitFor(() => expect(mockedGet).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
