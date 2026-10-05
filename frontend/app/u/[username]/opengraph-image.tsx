import { ImageResponse } from "next/og";
import { BRAND_SVG_DATA_URI } from "../../../lib/brand-svg";
import { usernameFromRouteParam } from "../../../lib/share";

export const alt = "DevLens portföy analizi";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage({ params }: { params: Promise<{ username: string }> }) {
  const username = usernameFromRouteParam((await params).username);
  const handle = username ? `@${username}` : "GitHub portföyü";

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 72, background: "linear-gradient(135deg, #f0fdfa 0%, #ffffff 55%, #f1f5f9 100%)", color: "#0f172a" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {/* eslint-disable-next-line @next/next/no-img-element -- rendered to a PNG by ImageResponse */}
          <img src={BRAND_SVG_DATA_URI} width={72} height={72} alt="" />
          <div style={{ display: "flex", fontSize: 44, fontWeight: 700 }}>
            <span>Dev</span>
            <span style={{ color: "#115e59" }}>Lens</span>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ fontSize: 30, color: "#0f766e", letterSpacing: 4 }}>PORTFÖY ANALİZİ</div>
          <div style={{ fontSize: handle.length > 22 ? 72 : 96, fontWeight: 700, lineHeight: 1.05 }}>{handle}</div>
          <div style={{ fontSize: 34, color: "#475569", maxWidth: 900 }}>Herkese açık GitHub kanıtlarına dayalı, deterministik portföy skoru.</div>
        </div>
        <div style={{ fontSize: 28, color: "#64748b" }}>devlens.barissurkit.com</div>
      </div>
    ),
    size,
  );
}
