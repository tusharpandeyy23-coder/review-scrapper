import pandas as pd
import streamlit as st
from dotenv import load_dotenv
load_dotenv()
from src.constants import SESSION_PRODUCT_KEY
from src.scrapper.scrape import ScrapeReviews

st.set_page_config(
    "myntra-review-scrapper"
)

st.title("Myntra Review Scrapper")

# Initialize session state
if "data" not in st.session_state:
    st.session_state["data"] = False
if "scrapped_data" not in st.session_state:
    st.session_state["scrapped_data"] = None


def form_input():
    product = st.text_input("Search Products")
    st.session_state[SESSION_PRODUCT_KEY] = product
    no_of_products = st.number_input("No of products to search",
                                     step=1,
                                     min_value=1)

    if st.button("Scrape Reviews"):
        if not product or product.strip() == "":
            st.error("❌ Please enter a product name to search.")
            return

        try:
            with st.spinner("🔍 Scraping reviews... This may take a minute..."):
                scrapper = ScrapeReviews(
                    product_name=product,
                    no_of_products=int(no_of_products)
                )

                scrapped_data = scrapper.get_review_data()

        except Exception as e:
            st.error(f"❌ Scraping failed: {e}")
            st.info("💡 This can happen if Chrome/Chromium is not available or if the website is blocking requests from this server.")
            return

        if scrapped_data is not None and not scrapped_data.empty:
            st.session_state["data"] = True
            st.session_state["scrapped_data"] = scrapped_data
            st.success(f"✅ Found {len(scrapped_data)} reviews!")

            # Try to store in MongoDB (optional)
            try:
                from src.cloud_io import MongoIO
                mongoio = MongoIO()
                mongoio.store_reviews(product_name=product,
                                      reviews=scrapped_data)
                st.success("✅ Data stored in MongoDB successfully!")
            except Exception as e:
                st.warning(f"⚠️ Could not store to MongoDB (data is saved to data.csv instead): {e}")

        else:
            st.warning("⚠️ No reviews found for this product. Try a different search term.")

    # Always display data if available (persists across re-renders)
    if st.session_state["scrapped_data"] is not None:
        st.subheader("📋 Scraped Reviews")
        st.dataframe(st.session_state["scrapped_data"], use_container_width=True)


form_input()
