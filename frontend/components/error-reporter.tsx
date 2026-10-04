"use client";

import { useEffect } from "react";
import { reportClientError } from "../lib/report-error";

/** Reports uncaught script errors and unhandled promise rejections. Renders nothing. */
export function ErrorReporter() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => reportClientError("script", event.error ?? event.message);
    const onRejection = (event: PromiseRejectionEvent) => reportClientError("promise", event.reason);
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
  return null;
}
