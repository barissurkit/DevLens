import "@testing-library/jest-dom/vitest";

// jsdom does not implement scrolling; components scroll after tab changes.
window.scrollTo = () => undefined;
