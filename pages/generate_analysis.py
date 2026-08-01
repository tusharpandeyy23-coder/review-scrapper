import pandas as pd
import streamlit as st
import os
from src.constants import SESSION_PRODUCT_KEY
from src.data_report.generate_data_report import DashboardGenerator

# Page Configuration
st.set_page_config(
    page_title="Myntra Review Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Load Custom CSS
css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "css", "main.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📊 Myntra Product Sentiment & Review Analytics")
st.markdown("Visual sentiment dashboard, rating distributions, price comparisons, and customer feedback breakdowns.")
st.markdown("---")


def load_review_data():
    """Load current in-memory dataset, fall back to MongoDB or local data.csv"""
    # 1. Check Streamlit session memory
    if st.session_state.get("scrapped_data") is not None:
        return st.session_state["scrapped_data"]

    # 2. Try MongoDB Cloud Storage
    try:
        from src.cloud_io import MongoIO
        mongo = MongoIO()
        product_name = st.session_state.get(SESSION_PRODUCT_KEY)
        if product_name:
            data = mongo.get_reviews(product_name=product_name)
            if data is not None and not data.empty:
                st.info(f"☁️ Loaded dataset from MongoDB Atlas for query: **'{product_name}'**")
                return data
    except Exception:
        pass

    # 3. Fall back to local data.csv file
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.csv")
    if os.path.exists(csv_path):
        try:
            data = pd.read_csv(csv_path)
            if not data.empty:
                st.info("📂 Loaded dataset from local `data.csv`")
                return data
        except Exception:
            pass

    return None


def main():
    data = load_review_data()

    if data is not None and not data.empty:
        # Display dataset preview
        with st.expander("📋 Preview Raw Scraped Dataset", expanded=False):
            st.dataframe(data, use_container_width=True)

        dashboard = DashboardGenerator(data)
        
        # Display General Visual Information & Charts
        dashboard.display_general_info()
        
        st.markdown("---")
        
        # Display Product Specific Sections & Review Summaries
        dashboard.display_product_sections()
    else:
        st.warning("⚠️ No dataset available for analysis yet.")
        st.info("👈 Please navigate to the **app** page in the sidebar menu, enter a product query, and click **Start Scraping**.")


if __name__ == "__main__":
    main()
