import pandas as pd
import streamlit as st
import time
import os
from dotenv import load_dotenv

load_dotenv()

from src.constants import SESSION_PRODUCT_KEY
from src.scrapper.scrape import ScrapeReviews

# Page Configuration
st.set_page_config(
    page_title="Myntra Review Scrapper & Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
css_path = os.path.join(os.path.dirname(__file__), "static", "css", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize Session State
if "data" not in st.session_state:
    st.session_state["data"] = False
if "scrapped_data" not in st.session_state:
    st.session_state["scrapped_data"] = None

# Hero Header
st.markdown("""
<div class="main-header">
    <h1>🛍️ Myntra Review Scrapper</h1>
    <p>High-Performance In-House Web Scrapper & Sentiment Analytics Engine</p>
    <div style="margin-top: 1rem;">
        <span class="badge-fast">⚡ High-Speed Direct Engine</span> &nbsp;
        <span class="badge-fast" style="background: rgba(139, 92, 246, 0.2); color: #c084fc; border-color: rgba(139, 92, 246, 0.4);">🛡️ In-House Scraper</span> &nbsp;
        <span class="badge-fast" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; border-color: rgba(59, 130, 246, 0.4);">🎯 Range: 1 - 100 Products</span>
    </div>
</div>
""", unsafe_allow_html=True)


def load_sample_dataset():
    """Load local data.csv sample dataset for demonstration"""
    csv_path = os.path.join(os.path.dirname(__file__), "data.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if not df.empty:
            st.session_state["data"] = True
            st.session_state["scrapped_data"] = df
            st.rerun()


def main():
    # Sidebar Configuration & Help
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info("💡 **Tip:** Search for any fashion item or brand (e.g., *nike shoes*, *t-shirts*, *jackets*, *jeans*).")
        
        st.markdown("---")
        st.markdown("### 📌 Scraper Features")
        st.markdown("""
        - 🚀 **Fast Direct Requests Engine**
        - 🔄 **Rotating User-Agent Headers**
        - 📦 **Supports 1 to 100 Products**
        - 💾 **Auto-saves to CSV & Cloud**
        """)
        
        st.markdown("---")
        if st.session_state["scrapped_data"] is not None:
            st.success("✅ Dataset currently loaded in memory.")
            if st.button("🗑️ Clear Current Data"):
                st.session_state["data"] = False
                st.session_state["scrapped_data"] = None
                st.rerun()

    # Search Form & Controls
    col_input, col_num = st.columns([3, 2])
    
    with col_input:
        product_query = st.text_input(
            "🔍 Product Search Query",
            placeholder="e.g. nike shoes, t-shirts, jackets...",
            help="Enter product name or brand to search on Myntra."
        )
    
    with col_num:
        no_of_products = st.slider(
            "📦 Number of Products to Scrape (1 - 100)",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            help="Select how many products to scrape from search catalog (max 100)."
        )

    st.session_state[SESSION_PRODUCT_KEY] = product_query

    col_btn, col_demo = st.columns([1, 1])
    with col_btn:
        scrape_clicked = st.button("🚀 Start Scraping", type="primary", use_container_width=True)
    with col_demo:
        demo_clicked = st.button("📂 Load Demo Dataset", use_container_width=True)

    if demo_clicked:
        load_sample_dataset()

    # Scraping Execution & Progress Bar
    if scrape_clicked:
        if not product_query or not product_query.strip():
            st.error("❌ Please enter a valid product query before starting.")
            return

        progress_text = st.empty()
        progress_bar = st.progress(0)

        def ui_status_callback(msg: str, level: str = "info"):
            if "%]" in msg:
                try:
                    pct = int(msg.split("%]")[0].replace("[", "").strip())
                    progress_bar.progress(min(100, max(0, pct)))
                    progress_text.markdown(f"**Fetching products & reviews... ({pct}%)**")
                except Exception:
                    pass

        try:
            progress_text.markdown("**🚀 Initiating scraper engine...**")
            scrapper = ScrapeReviews(
                product_name=product_query,
                no_of_products=no_of_products
            )

            df = scrapper.get_review_data(status_callback=ui_status_callback)
            progress_bar.progress(100)
            progress_text.empty()

            if df is not None and not df.empty:
                st.session_state["data"] = True
                st.session_state["scrapped_data"] = df
                st.success(f"🎉 Successfully scraped {len(df)} customer review entries!")

                try:
                    from src.cloud_io import MongoIO
                    mongo_io = MongoIO()
                    mongo_io.store_reviews(product_name=product_query, reviews=df)
                    st.success("☁️ Stored successfully in MongoDB Atlas!")
                except Exception as mongo_err:
                    st.info("💾 Saved data to local CSV (`data.csv`)")

            else:
                st.warning("⚠️ No products were returned for this query on the current host IP.")
                st.info("""
                💡 **Cloud Datacenter IP Notice**:
                Myntra's CDN restricts direct automated requests originating from US/EU cloud datacenter IP ranges (such as Render/AWS).
                - **To scrape live on cloud hosts**: Add a `PROXY_URL` environment variable in Render.
                - **To run live directly**: Run the app locally on your machine where residential IPs work 100%.
                - **Or click 'Load Demo Dataset' above** to instantly evaluate the dashboard and analytics!
                """)

        except Exception as err:
            progress_text.empty()
            st.error(f"❌ Scraping encountered an error: {err}")
            st.info("💡 Tip: Verify your network connection or try a different product query.")

    # Results Section & Metrics Dashboard
    if st.session_state["scrapped_data"] is not None:
        df = st.session_state["scrapped_data"]
        
        st.markdown("---")
        st.subheader("📊 Scraped Dataset Metrics")
        
        m1, m2, m3, m4 = st.columns(4)
        
        total_reviews = len(df)
        unique_prods = df["Product Name"].nunique()
        
        try:
            prices = pd.to_numeric(df["Price"].astype(str).str.replace("₹", "").str.replace(",", "").str.strip(), errors="coerce")
            avg_price = f"₹{prices.mean():.2f}" if not prices.isna().all() else "N/A"
        except Exception:
            avg_price = "N/A"

        try:
            ratings = pd.to_numeric(df["Rating"], errors="coerce")
            avg_rating = f"⭐ {ratings.mean():.2f}" if not ratings.isna().all() else "N/A"
        except Exception:
            avg_rating = "N/A"

        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{unique_prods}</div>
                <div class="metric-label">Products Scraped</div>
            </div>
            """, unsafe_allow_html=True)

        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{total_reviews}</div>
                <div class="metric-label">Total Reviews</div>
            </div>
            """, unsafe_allow_html=True)

        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #38bdf8;">{avg_price}</div>
                <div class="metric-label">Avg Product Price</div>
            </div>
            """, unsafe_allow_html=True)

        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val" style="color: #f59e0b;">{avg_rating}</div>
                <div class="metric-label">Avg Customer Rating</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Data Table View & Export
        st.subheader("📋 Product Reviews Data Table")
        
        search_filter = st.text_input("🔎 Search inside scraped dataset", placeholder="Filter by keyword, name, or comment...")
        
        filtered_df = df
        if search_filter:
            mask = df.astype(str).apply(lambda row: row.str.contains(search_filter, case=False).any(), axis=1)
            filtered_df = df[mask]

        st.dataframe(filtered_df, use_container_width=True, height=380)

        # Export Buttons
        col_dl1, col_dl2, _ = st.columns([1, 1, 2])
        with col_dl1:
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV Dataset",
                data=csv_data,
                file_name=f"myntra_reviews_{int(time.time())}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_dl2:
            json_data = filtered_df.to_json(orient="records", indent=2).encode('utf-8')
            st.download_button(
                label="📄 Download JSON Dataset",
                data=json_data,
                file_name=f"myntra_reviews_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True
            )

        st.markdown("---")
        st.success("💡 **Next Step:** Navigate to the **generate_analysis** page in the sidebar menu to view full visual Plotly charts and sentiment breakdowns!")


if __name__ == "__main__":
    main()
