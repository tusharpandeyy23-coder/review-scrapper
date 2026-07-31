import pandas as pd
import streamlit as st
from dotenv import load_dotenv
load_dotenv()
from src.cloud_io import MongoIO
from src.constants import SESSION_PRODUCT_KEY
from src.scrapper.scrape import ScrapeReviews

st.set_page_config(
    "myntra-review-scrapper"

)

st.title("Myntra Review Scrapper")
st.session_state["data"] = False


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
            st.success(f"✅ Found {len(scrapped_data)} reviews!")
            try:
                mongoio = MongoIO()
                mongoio.store_reviews(product_name=product,
                                      reviews=scrapped_data)
                st.success("✅ Data stored in MongoDB successfully!")
            except Exception as e:
                st.warning(f"⚠️ Could not store to MongoDB (data is saved to data.csv instead): {e}")

            st.dataframe(scrapped_data)
        else:
            st.warning("⚠️ No reviews found for this product. Try a different search term.")


if __name__ == "__main__":
    data = form_input()
