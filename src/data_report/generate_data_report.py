import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os, sys
from src.exception import CustomException


class DashboardGenerator:
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()

    def _prepare_data(self):
        """Clean and convert data columns for Plotly visualizations"""
        try:
            # Clean Price column
            if 'Price' in self.data.columns:
                self.data['Price_Clean'] = pd.to_numeric(
                    self.data['Price'].astype(str)
                    .str.replace("₹", "")
                    .str.replace(",", "")
                    .str.strip(),
                    errors='coerce'
                ).fillna(0)
            else:
                self.data['Price_Clean'] = 0

            # Clean Overall Rating column
            if 'Over_All_Rating' in self.data.columns:
                self.data['Over_All_Rating'] = pd.to_numeric(
                    self.data['Over_All_Rating'], errors='coerce'
                ).fillna(0)
            else:
                self.data['Over_All_Rating'] = 0

            # Clean Individual User Rating column
            if 'Rating' in self.data.columns:
                self.data['Rating_Clean'] = pd.to_numeric(
                    self.data['Rating'], errors='coerce'
                ).fillna(0)
            else:
                self.data['Rating_Clean'] = 0
        except Exception as e:
            print(f"[WARN] Data preparation issue: {e}")

    def display_general_info(self):
        st.subheader("📊 General Product & Sentiment Analytics")
        self._prepare_data()

        c1, c2 = st.columns(2)

        with c1:
            # Pie chart: Average Rating by Product
            avg_ratings = (
                self.data.groupby('Product Name', as_index=False)['Over_All_Rating']
                .mean()
                .dropna()
            )
            if not avg_ratings.empty:
                fig_pie = px.pie(
                    avg_ratings,
                    values='Over_All_Rating',
                    names='Product Name',
                    title='⭐ Average Ratings Distribution by Product',
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pie.update_layout(showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            # Bar chart: Average Price Comparison
            avg_prices = (
                self.data.groupby('Product Name', as_index=False)['Price_Clean']
                .mean()
                .dropna()
            )
            if not avg_prices.empty:
                fig_bar = px.bar(
                    avg_prices,
                    x='Product Name',
                    y='Price_Clean',
                    color='Product Name',
                    title='💰 Average Price Comparison (₹)',
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_bar.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Price (₹)")
                st.plotly_chart(fig_bar, use_container_width=True)

    def display_product_sections(self):
        st.subheader("🛍️ Individual Product Deep Dives")
        self._prepare_data()

        product_names = self.data['Product Name'].unique()
        
        for i, product_name in enumerate(product_names):
            product_data = self.data[self.data['Product Name'] == product_name]
            
            with st.expander(f"📦 Product #{i+1}: {product_name}", expanded=(i == 0)):
                col_info, col_chart = st.columns([1, 1])

                with col_info:
                    avg_price = product_data['Price_Clean'].mean()
                    avg_rating = product_data['Over_All_Rating'].mean()
                    total_reviews = len(product_data)

                    st.markdown(f"**💰 Price:** ₹{avg_price:.2f}")
                    st.markdown(f"**⭐ Overall Rating:** {avg_rating:.2f} / 5.0")
                    st.markdown(f"**💬 Extracted Reviews:** {total_reviews}")

                    # Top Positive Reviews
                    pos_revs = product_data[product_data['Rating_Clean'] >= 4.0].head(3)
                    if not pos_revs.empty:
                        st.markdown("#### ✨ Top Customer Highlights")
                        for _, r in pos_revs.iterrows():
                            st.markdown(f"⭐ **{r.get('Rating_Clean', 5)}/5** ({r.get('Name', 'Customer')}): *\"{r.get('Comment', '')}\"*")

                    # Top Negative Reviews
                    neg_revs = product_data[product_data['Rating_Clean'] <= 2.5].head(3)
                    if not neg_revs.empty:
                        st.markdown("#### 💢 Critical Feedback")
                        for _, r in neg_revs.iterrows():
                            st.markdown(f"⚠️ **{r.get('Rating_Clean', 1)}/5** ({r.get('Name', 'Customer')}): *\"{r.get('Comment', '')}\"*")

                with col_chart:
                    # User Rating Breakdown Bar Chart
                    rating_counts = (
                        product_data['Rating_Clean']
                        .value_counts()
                        .reset_index()
                    )
                    rating_counts.columns = ['Rating', 'Count']
                    
                    if not rating_counts.empty:
                        fig = px.bar(
                            rating_counts,
                            x='Rating',
                            y='Count',
                            title=f"Star Rating Breakdown for {product_name[:30]}...",
                            color='Rating',
                            color_continuous_scale=px.colors.sequential.Viridis
                        )
                        st.plotly_chart(fig, use_container_width=True)
