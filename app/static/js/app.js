/* ============================================================
   KRISHIRATE — GLOBAL APPLICATION
   Dashboard data + shared frontend utilities
   ============================================================ */

(() => {
    "use strict";


    /* ========================================================
       CONFIGURATION
       ======================================================== */

    const API = {
        dashboard: "/api/dashboard",
    };


    /* ========================================================
       DOM HELPERS
       ======================================================== */

    function select(selector, parent = document) {
        return parent.querySelector(selector);
    }


    function selectAll(selector, parent = document) {
        return [...parent.querySelectorAll(selector)];
    }


    function formatNumber(value) {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        const number = Number(value);

        if (Number.isNaN(number)) {
            return value;
        }

        return new Intl.NumberFormat("en-IN", {
            maximumFractionDigits: 2,
        }).format(number);
    }


    function formatPrice(value) {
        if (value === null || value === undefined || value === "") {
            return "—";
        }

        return `रु. ${formatNumber(value)}`;
    }


    /* ========================================================
       DASHBOARD
       ======================================================== */

    async function loadDashboard() {

        const dashboard = select("[data-dashboard]");

        if (!dashboard) {
            return;
        }

        setDashboardLoading(true);

        try {

            const response = await fetch(API.dashboard, {
                method: "GET",
                headers: {
                    "Accept": "application/json",
                },
            });

            if (!response.ok) {
                throw new Error(
                    `Dashboard request failed: ${response.status}`
                );
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(
                    data.error || "Unable to load dashboard data."
                );
            }

            renderDashboard(data);

        } catch (error) {

            console.error(
                "KrishiRate dashboard error:",
                error
            );

            showDashboardError();

        } finally {

            setDashboardLoading(false);

        }
    }


    /* ========================================================
       RENDER DASHBOARD
       ======================================================== */

    function renderDashboard(data) {

        const statistics = data.statistics || {};
        const prices = data.latest_prices || [];
        const source = data.latest_source || null;


        /* ----------------------------------------------------
           STATISTICS
        ---------------------------------------------------- */

        setText(
            "[data-stat='markets']",
            formatNumber(statistics.active_markets)
        );

        setText(
            "[data-stat='products']",
            formatNumber(statistics.active_products)
        );

        setText(
            "[data-stat='records']",
            formatNumber(statistics.total_price_records)
        );


        /* ----------------------------------------------------
           DATA STATUS
        ---------------------------------------------------- */

        const latestDate = statistics.latest_price_date;

        if (latestDate) {
            setText(
                "[data-stat='date']",
                formatDate(latestDate)
            );
        }


        /* ----------------------------------------------------
           SOURCE
        ---------------------------------------------------- */

        if (source) {

            setText(
                "[data-source-name]",
                source.name
            );

            setText(
                "[data-source-organization]",
                source.organization
            );

        }


        /* ----------------------------------------------------
           LATEST PRICE TABLE
        ---------------------------------------------------- */

        renderLatestPrices(prices);

    }


    /* ========================================================
       LATEST PRICES
       ======================================================== */

    function renderLatestPrices(prices) {

        const tableBody = select(
            "[data-latest-prices]"
        );

        if (!tableBody) {
            return;
        }


        if (!prices.length) {

            tableBody.innerHTML = `
                <tr>
                    <td
                        colspan="7"
                        class="table-empty"
                    >
                        No price data available.
                    </td>
                </tr>
            `;

            return;
        }


        tableBody.innerHTML = prices
            .map((price) => {

                const productName =
                    price.product ||
                    price.nepali_name ||
                    price.english_name ||
                    "Unknown product";

                const market =
                    price.market ||
                    "Unknown market";

                const unit =
                    price.unit ||
                    "—";

                const freshness =
                    price.freshness ||
                    "UNKNOWN";

                const freshnessClass =
                    freshness.toLowerCase();


                return `
                    <tr>

                        <td>
                            <div class="product-cell">

                                <strong>
                                    ${escapeHtml(productName)}
                                </strong>

                                <span>
                                    ${escapeHtml(
                                        price.product_source_code || ""
                                    )}
                                </span>

                            </div>
                        </td>


                        <td>
                            ${escapeHtml(market)}
                        </td>


                        <td>
                            <span class="price">
                                ${formatPrice(price.minimum)}
                            </span>
                        </td>


                        <td>
                            <strong class="average-price">
                                ${formatPrice(price.average)}
                            </strong>
                        </td>


                        <td>
                            ${formatPrice(price.maximum)}
                        </td>


                        <td>
                            ${escapeHtml(unit)}
                        </td>


                        <td>
                            <span
                                class="freshness ${freshnessClass}"
                            >
                                ${escapeHtml(freshness)}
                            </span>
                        </td>

                    </tr>
                `;

            })
            .join("");

    }


    /* ========================================================
       LOADING STATE
       ======================================================== */

    function setDashboardLoading(isLoading) {

        const dashboard = select(
            "[data-dashboard]"
        );

        if (!dashboard) {
            return;
        }

        dashboard.classList.toggle(
            "is-loading",
            isLoading
        );

    }


    /* ========================================================
       ERROR STATE
       ======================================================== */

    function showDashboardError() {

        const tableBody = select(
            "[data-latest-prices]"
        );

        if (tableBody) {

            tableBody.innerHTML = `
                <tr>
                    <td
                        colspan="7"
                        class="table-empty table-error"
                    >
                        Unable to load the latest market data.
                        Please refresh the page.
                    </td>
                </tr>
            `;

        }


        const status = select(
            "[data-stat='date']"
        );

        if (status) {
            status.textContent = "Unavailable";
        }

    }


    /* ========================================================
       TEXT HELPERS
       ======================================================== */

    function setText(selector, value) {

        const element = select(selector);

        if (!element) {
            return;
        }

        element.textContent = value;

    }


    /* ========================================================
       DATE FORMATTING
       ======================================================== */

    function formatDate(value) {

        if (!value) {
            return "—";
        }

        const date = new Date(`${value}T00:00:00`);

        if (Number.isNaN(date.getTime())) {
            return value;
        }

        return new Intl.DateTimeFormat("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
        }).format(date);

    }


    /* ========================================================
       HTML ESCAPING
       ======================================================== */

    function escapeHtml(value) {

        if (
            value === null ||
            value === undefined
        ) {
            return "";
        }

        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");

    }


    /* ========================================================
       INITIALIZATION
       ======================================================== */

    function initialize() {

        loadDashboard();

    }


    if (document.readyState === "loading") {

        document.addEventListener(
            "DOMContentLoaded",
            initialize
        );

    } else {

        initialize();

    }

})();