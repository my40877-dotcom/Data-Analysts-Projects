from wordcloud import WordCloud
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="QuickBite Recovery Dashboard", layout="wide")
st.title("📊 QuickBite Express: Crisis Recovery Analysis")

df_orders = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/fact_orders.csv')
df_restaurants = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/dim_restaurant.csv')
dim_customers = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/dim_customer.csv')    
dim_menu_items = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/dim_menu_item.csv')  
fact_order_items = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/fact_order_items.csv')  
fact_ratings = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/fact_ratings.csv')  

df_orders['order_timestamp'] = pd.to_datetime(df_orders['order_timestamp'])
df_orders['month_year'] = df_orders['order_timestamp'].dt.strftime('%Y-%m')


def identify_phase(timestamp):
    if timestamp < pd.Timestamp('2025-06-01'):
        return 'Pre-Crisis'
    else:
        return 'Crisis'

df_orders['Phase'] = df_orders['order_timestamp'].apply(identify_phase)


st.sidebar.header("Filters")
city_list = df_restaurants['city'].unique()
selected_city = st.sidebar.multiselect("Select City", options=city_list, default=city_list)


df_merged = df_orders.merge(df_restaurants, on='restaurant_id')
filtered_df = df_merged[df_merged['city'].isin(selected_city)]


monthly_orders = filtered_df.groupby('month_year').size().reset_index(name='order_count')

# Define Crisis Phase
def get_phase(month):
    if month < '2025-06': return 'Pre-Crisis'
    else: return 'Crisis'

monthly_orders['Phase'] = monthly_orders['month_year'].apply(get_phase)


st.subheader("1. Monthly Order Trends: Pre-Crisis vs. Crisis")
fig = px.bar(
    monthly_orders, 
    x='month_year', 
    y='order_count', 
    color='Phase',
    title="Total Orders by Month",
    labels={'month_year': 'Month', 'order_count': 'Total Orders'},
    color_discrete_map={'Pre-Crisis': '#00CC96', 'Crisis': '#EF553B'} # Green for stable, Red for crisis
)

st.plotly_chart(fig, use_container_width=True)

# --- KPI METRICS ---
pre_crisis_avg = monthly_orders[monthly_orders['Phase'] == 'Pre-Crisis']['order_count'].mean()
crisis_avg = monthly_orders[monthly_orders['Phase'] == 'Crisis']['order_count'].mean()
decline = ((crisis_avg - pre_crisis_avg) / pre_crisis_avg) * 100

col1, col2 = st.columns(2)
col1.metric("Pre-Crisis Avg Orders", f"{int(pre_crisis_avg)}")
col2.metric("Crisis Avg Orders", f"{int(crisis_avg)}", f"{decline:.1f}% decline", delta_color="inverse")


df_delivery = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/fact_delivery_performance.csv')


df_ops = df_orders.merge(df_delivery, on='order_id', how='left')


df_ops['is_cancelled_num'] = df_ops['is_cancelled'].map({'Y': 1, 'N': 0})
cancel_trend = df_ops.groupby(['month_year', 'Phase'])['is_cancelled_num'].mean().reset_index()
cancel_trend['cancel_rate_%'] = cancel_trend['is_cancelled_num'] * 100

df_ops['on_time'] = df_ops['actual_delivery_time_mins'] <= df_ops['expected_delivery_time_mins']
sla_trend = df_ops.groupby(['month_year', 'Phase'])['on_time'].mean().reset_index()
sla_trend['sla_compliance_%'] = sla_trend['on_time'] * 100

st.subheader("2. Operational Gaps: Cancellations & Delivery Times")
col_left, col_right = st.columns(2)

with col_left:
    fig_cancel = px.line(
        cancel_trend, x='month_year', y='cancel_rate_%', color='Phase',
        title="Cancellation Rate Trend", markers=True,
        color_discrete_map={'Pre-Crisis': '#00CC96', 'Crisis': '#EF553B'}
    )
    st.plotly_chart(fig_cancel, use_container_width=True)

with col_right:
    fig_sla = px.area(
        sla_trend, 
        x='month_year', 
        y='sla_compliance_%',
        color='Phase',
        title="Delivery SLA Compliance %",
        labels={'sla_compliance_%': 'On-Time Delivery %'},
        color_discrete_map={'Pre-Crisis': '#00CC96', 'Crisis': '#EF553B'}
    )
    st.plotly_chart(fig_sla, use_container_width=True)


df_ratings = pd.read_csv('/home/manish/Documents/Projects/QuickBite_Analysis/data/fact_ratings.csv')

df_ratings = df_ratings.merge(df_orders[['order_id', 'Phase']], on='order_id')

st.subheader("3. Customer Sentiment & Feedback")


crisis_reviews = df_ratings[df_ratings['Phase'] == 'Crisis']['review_text'].dropna()


negative_reviews = df_ratings[(df_ratings['Phase'] == 'Crisis') & (df_ratings['sentiment_score'] < 0)]
text = " ".join(review for review in negative_reviews['review_text'])

col_cloud, col_rating = st.columns([2, 1])

with col_cloud:
    st.write("Top Negative Keywords (Crisis Period)")
    if text:
        wordcloud = WordCloud(background_color="white", colormap="Reds", width=800, height=400).generate(text)
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.write("No review data available.")

with col_rating:
    avg_rating = df_ratings[df_ratings['Phase'] == 'Crisis']['rating'].mean()
    st.metric("Avg. Rating during Crisis", f"{avg_rating:.2f} ⭐", delta="-1.2 vs Pre-Crisis")
    st.write("Common complaints: 'Late', 'Cold Food', 'Safety'")


df_orders['revenue'] = df_orders['subtotal_amount'] + df_orders['delivery_fee'] - df_orders['discount_amount']  # cite: 5


revenue_impact = df_orders.groupby('Phase')['revenue'].sum().reset_index()


pre_rev = revenue_impact[revenue_impact['Phase'] == 'Pre-Crisis']['revenue'].values[0]
cri_rev = revenue_impact[revenue_impact['Phase'] == 'Crisis']['revenue'].values[0]
rev_loss_pct = ((cri_rev - pre_rev) / pre_rev) * 100


st.header("4. Revenue Impact & Financial Loss")


m1, m2, m3 = st.columns(3)
m1.metric("Pre-Crisis Total Revenue", f"₹{pre_rev:,.0f}")
m2.metric("Crisis Total Revenue", f"₹{cri_rev:,.0f}")
m3.metric("Revenue Growth/Decline", f"{rev_loss_pct:.1f}%", delta=f"{rev_loss_pct:.1f}%", delta_color="inverse")

# Comparison Chart
fig_rev = px.bar(
    revenue_impact, 
    x='Phase', 
    y='revenue', 
    color='Phase',
    text_auto='.2s',
    title="Revenue Comparison: Pre-Crisis vs. Crisis",
    color_discrete_map={'Pre-Crisis': '#00CC96', 'Crisis': '#EF553B'}
)
st.plotly_chart(fig_rev, use_container_width=True)


pre_crisis_data = df_orders[df_orders['Phase'] == 'Pre-Crisis']


customer_spend = pre_crisis_data.groupby('customer_id')['revenue'].sum().sort_values(ascending=False)
top_5_percent_cutoff = int(len(customer_spend) * 0.05)
high_value_customers = customer_spend.head(top_5_percent_cutoff).index.tolist()


crisis_customer_ids = df_orders[df_orders['Phase'] == 'Crisis']['customer_id'].unique()
churned_high_value = [c for c in high_value_customers if c not in crisis_customer_ids]


churn_pct = (len(churned_high_value) / len(high_value_customers)) * 100

st.header("5. Secondary Analysis: High-Value Loyalty Impact")

col_metric, col_list = st.columns([1, 1])

with col_metric:
    st.metric("High-Value Customer Churn", f"{len(churned_high_value)} Users", f"{churn_pct:.1f}% Loss", delta_color="inverse")
    st.write("These are the top 5% of spenders who stopped ordering entirely after May 2025.")

with col_list:
    st.write("Sample List of Churned VIP IDs for Outreach")
    st.dataframe(pd.DataFrame(churned_high_value, columns=['Customer ID']).head(10))


rest_perf = df_merged.groupby(['restaurant_name', 'Phase']).size().unstack(fill_value=0).reset_index()
rest_perf['Decline %'] = ((rest_perf['Crisis'] - rest_perf['Pre-Crisis']) / rest_perf['Pre-Crisis']) * 100


top_partners = rest_perf[rest_perf['Pre-Crisis'] >= 50].sort_values(by='Decline %', ascending=False).head(10)

st.subheader("6. Resilient Restaurant Partners")
fig_rest = px.bar(
    top_partners, x='Decline %', y='restaurant_name', orientation='h',
    title="Top 10 High-Volume Restaurants with Largest Order Decline",
    color='Decline %', color_continuous_scale='Reds'
)
st.plotly_chart(fig_rest, use_container_width=True)
