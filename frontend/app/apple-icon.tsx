import { ImageResponse } from "next/og";
import { BRAND_SVG_DATA_URI } from "../lib/brand-svg";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#ffffff" }}>
        {/* eslint-disable-next-line @next/next/no-img-element -- rendered to a PNG by ImageResponse, not shown in the page */}
        <img src={BRAND_SVG_DATA_URI} width={150} height={150} alt="" />
      </div>
    ),
    size,
  );
}
