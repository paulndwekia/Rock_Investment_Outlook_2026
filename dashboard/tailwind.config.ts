import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#121A23",
        paper: "#F5F4F0",
        gold: "#B89552",
        goldSoft: "#E8D9B8",
        positive: "#237A5A",
        negative: "#B34D4D",
        muted: "#77818A"
      },
      boxShadow: { soft: "0 18px 50px rgba(26, 32, 38, .07)" }
    }
  },
  plugins: []
};
export default config;