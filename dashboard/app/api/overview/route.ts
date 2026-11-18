import { NextResponse } from "next/server";
import { fetchPDMODomesticDebt } from "@/lib/public-data";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  const baseUrl = process.env.DATA_API_URL?.replace(/\/$/, "");
  const token = process.env.DATA_API_TOKEN;

  if (baseUrl && token) {
    try {
      const response = await fetch(`${baseUrl}/v1/overview`, {
        cache: "no-store",
        headers: { "Accept": "application/json", "Authorization": `Bearer ${token}` },
        signal: AbortSignal.timeout(8000)
      });
      if (response.ok) {
        const payload = await response.json();
        return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
      }
    } catch {
      // Fall through to the public government dataset rather than leaving the workspace empty.
    }
  }

  try {
    const { overview } = await fetchPDMODomesticDebt();
    return NextResponse.json(overview, {
      headers: { "Cache-Control": "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400" }
    });
  } catch {
    return NextResponse.json({
      status: "unavailable",
      message: "Neither the authorised research API nor the public PDMO data source is currently reachable. No market figures are simulated."
    }, { status: 200, headers: { "Cache-Control": "no-store" } });
  }
}
