import pandas as pd
import streamlit as st
import os
from src.constants import SESSION_PRODUCT_KEY
from src.data_report.generate_data_report import DashboardGenerator


def load_review_data():
    """Try loading data from MongoDB first, fall back to local CSV"""
    # Try MongoDB
    try:
        from src.cloud_io import MongoIO
        mongo = MongoIO()
        product_name = st.session_state.get(SESSION_PRODUCT_KEY)
        if product_name:
            data = mongo.get_reviews(product_name=product_name)
            if data is not None and not data.empty:
                return data
    except Exception as e:
        print(f"[WARN] MongoDB unavailable: {e}")

    # Fall back to local CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.csv")
    if os.path.exists(csv_path):
        data = pd.read_csv(csv_path)
        if not data.empty:
            st.info("📂 Loaded data from local CSV file (MongoDB unavailable)")
            return data

    return None


def create_analysis_page(review_data: pd.DataFrame):
    if review_data is not None and not review_data.empty:
        st.dataframe(review_data, use_container_width=True)
        if st.button("Generate Analysis"):
            dashboard = DashboardGenerator(review_data)

            # Display general information
            dashboard.display_general_info()

            # Display product-specific sections
            dashboard.display_product_sections()


try:
    has_data = st.session_state.get("data", False)

    if has_data:
        data = load_review_data()
        if data is not None:
            create_analysis_page(data)
        else:
            st.warning("⚠️ No data found. Please scrape some reviews first.")
    else:
        # Try loading from CSV anyway
        csv_path = "data.csv"
        if os.path.exists(csv_path):
            data = pd.read_csv(csv_path)
            if not data.empty:
                st.info("📂 Found existing data in data.csv")
                create_analysis_page(data)
            else:
                with st.sidebar:
                    st.markdown("""
                    No Data Available for analysis. Please Go to search page for analysis.
                    """)
        else:
            with st.sidebar:
                st.markdown("""
                No Data Available for analysis. Please Go to search page for analysis.
                """)

except AttributeError:
    st.markdown(""" # No Data Available for analysis.""")
except Exception as e:
    st.error(f"❌ Error: {e}")
