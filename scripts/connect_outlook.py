from pathlib import Path

app = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026" / "website" / "app.py"

text = app.read_text(encoding="utf-8")

marker = 'st.subheader("Evidence Checklist")'

if marker not in text:
    raise SystemExit(
        "Could not find the Evidence Checklist section. "
        "No changes were made."
    )

block = r'''
# ============================================================
# QUANTITATIVE MARKET EVIDENCE
# ============================================================

st.divider()

st.subheader(
    "Quantitative Market Evidence"
)

quant_path = (
    ROOT
    / "analysis"
    / "outlook_quant_metrics.json"
)

if quant_path.exists():

    try:

        with open(
            quant_path,
            "r",
            encoding="utf-8"
        ) as f:

            quant = json.load(f)

        st.caption(
            "These metrics are calculated from the cleaned "
            "Rock Data Plus observations stored locally. "
            "They describe observed historical conditions "
            "and are not forecasts or guaranteed returns."
        )

        # ----------------------------------------------------
        # MARKET RISK
        # ----------------------------------------------------

        risk_data = quant.get(
            "risk",
            {}
        )

        vol = (
            risk_data.get(
                "annualised_volatility"
            )
            or
            risk_data.get(
                "Annualised_Volatility"
            )
            or
            risk_data.get(
                "volatility"
            )
        )

        drawdown = (
            risk_data.get(
                "max_drawdown"
            )
            or
            risk_data.get(
                "Maximum_Drawdown"
            )
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            if vol is not None:

                st.metric(
                    "Observed Annualised Volatility",
                    f"{float(vol) * 100:.2f}%"
                )

            else:

                st.metric(
                    "Observed Annualised Volatility",
                    "N/A"
                )

        with c2:

            if drawdown is not None:

                st.metric(
                    "Observed Maximum Drawdown",
                    f"{float(drawdown) * 100:.2f}%"
                )

            else:

                st.metric(
                    "Observed Maximum Drawdown",
                    "N/A"
                )

        # ----------------------------------------------------
        # TREASURY BILL CURVE
        # ----------------------------------------------------

        tb_data = quant.get(
            "treasury_bills",
            {}
        )

        spread = tb_data.get(
            "91d_364d_spread"
        )

        with c3:

            if spread is not None:

                st.metric(
                    "91D–364D Spread",
                    f"{float(spread):.2f} pp"
                )

            else:

                st.metric(
                    "91D–364D Spread",
                    "N/A"
                )

        # ----------------------------------------------------
        # FIXED INCOME STRUCTURE
        # ----------------------------------------------------

        st.markdown(
            "### Fixed Income Structure"
        )

        fc1, fc2, fc3 = st.columns(3)

        curve_data = quant.get(
            "yield_curve",
            {}
        )

        with fc1:

            short_yield = curve_data.get(
                "short_yield"
            )

            if short_yield is not None:

                st.metric(
                    "Short-End Yield",
                    f"{float(short_yield):.2f}%"
                )

            else:

                st.metric(
                    "Short-End Yield",
                    "N/A"
                )

        with fc2:

            long_yield = curve_data.get(
                "long_yield"
            )

            if long_yield is not None:

                st.metric(
                    "Long-End Yield",
                    f"{float(long_yield):.2f}%"
                )

            else:

                st.metric(
                    "Long-End Yield",
                    "N/A"
                )

        with fc3:

            curve_slope = curve_data.get(
                "long_short_spread"
            )

            if curve_slope is not None:

                st.metric(
                    "Curve Slope",
                    f"{float(curve_slope):.2f} pp"
                )

            else:

                st.metric(
                    "Curve Slope",
                    "N/A"
                )

        # ----------------------------------------------------
        # MACRO / BOND EVIDENCE
        # ----------------------------------------------------

        st.markdown(
            "### Macro & Government-Bond Evidence"
        )

        mc1, mc2, mc3 = st.columns(3)

        inflation_data = quant.get(
            "inflation",
            {}
        )

        bond_data = quant.get(
            "bond_index",
            {}
        )

        with mc1:

            latest_inflation = inflation_data.get(
                "latest_value"
            )

            if latest_inflation is not None:

                st.metric(
                    "Latest Rock Inflation",
                    f"{float(latest_inflation):.2f}%"
                )

            else:

                st.metric(
                    "Latest Rock Inflation",
                    "N/A"
                )

        with mc2:

            latest_bond = bond_data.get(
                "latest_value"
            )

            if latest_bond is not None:

                st.metric(
                    "Latest Bond Index",
                    f"{float(latest_bond):,.2f}"
                )

            else:

                st.metric(
                    "Latest Bond Index",
                    "N/A"
                )

        with mc3:

            bond_return = bond_data.get(
                "total_sample_return"
            )

            if bond_return is not None:

                st.metric(
                    "Bond Index Sample Return",
                    f"{float(bond_return) * 100:.2f}%"
                )

            else:

                st.metric(
                    "Bond Index Sample Return",
                    "N/A"
                )

        # ----------------------------------------------------
        # SCENARIO INPUTS
        # ----------------------------------------------------

        scenario_data = quant.get(
            "scenario_framework",
            {}
        )

        st.markdown(
            "### Scenario Inputs"
        )

        scenario_table = pd.DataFrame(
            [
                {
                    "Indicator":
                        "Observed annualised volatility",
                    "Value":
                        scenario_data.get(
                            "observed_volatility"
                        )
                },
                {
                    "Indicator":
                        "Yield-curve slope",
                    "Value":
                        scenario_data.get(
                            "curve_slope"
                        )
                },
                {
                    "Indicator":
                        "91D–364D Treasury Bill spread",
                    "Value":
                        scenario_data.get(
                            "tbill_91d_364d_spread"
                        )
                },
                {
                    "Indicator":
                        "Latest inflation",
                    "Value":
                        scenario_data.get(
                            "latest_inflation"
                        )
                }
            ]
        )

        st.dataframe(
            scenario_table,
            use_container_width=True,
            hide_index=True
        )

        st.info(
            "Scenario inputs are evidence variables. "
            "They are not presented as predictions of future "
            "market returns."
        )

    except Exception as exc:

        st.error(
            f"Quantitative evidence could not be loaded: {exc}"
        )

else:

    st.info(
        "Quantitative outlook metrics have not been generated yet."
    )

'''

text = text.replace(
    marker,
    block + "\n" + marker,
    1
)

app.write_text(
    text,
    encoding="utf-8"
)

print("✓ Quantitative evidence section added.")
print("✓ Existing Outlook content preserved.")
