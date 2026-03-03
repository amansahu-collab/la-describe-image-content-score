import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# MongoDB connection
@st.cache_resource
def get_database():
    client = MongoClient("mongodb+srv://shubhamgehlod_db_user:3HUdgGMZ10kMAvBa@languagetranscript.4hisuze.mongodb.net/?retryWrites=true&w=majority")
    db = client["LA_writing-database"]
    return db["Describe-image-remarks"]

# Fetch data
@st.cache_data(ttl=300)
def load_data():
    collection = get_database()
    data = list(collection.find())
    
    records = []
    for doc in data:
        score = doc.get('evaluation_response', {}).get('final_result', {}).get('score_out_of_90', 0)
        expected = doc.get('expected_score', 0)
        grounded = doc.get('evaluation_response', {}).get('agent_2_template_detector', {}).get('output', {}).get('evidence', {}).get('grounded_elements_found', [])
        template_signals = doc.get('evaluation_response', {}).get('agent_2_template_detector', {}).get('output', {}).get('evidence', {}).get('generic_template_signals', [])
        updated_score = doc.get('updated_model_score', {}).get('final_result', {}).get('score_out_of_90', None)
        
        records.append({
            'id': str(doc.get('_id', '')),
            'score': score,
            'expected_score': expected,
            'updated_score': updated_score if updated_score is not None else '-',
            'score_diff': abs(score - expected),
            'remark': doc.get('student_remark', ''),
            'is_template': doc.get('evaluation_response', {}).get('final_result', {}).get('is_template', False),
            'repetition_severity': doc.get('evaluation_response', {}).get('final_result', {}).get('repetition_analysis', {}).get('severity', ''),
            'feedback': doc.get('evaluation_response', {}).get('final_result', {}).get('final_feedback', ''),
            'transcription': doc.get('evaluation_response', {}).get('transcription', '')[:100] + '...',
            'grounded_elements': ', '.join(grounded[:3]) + ('...' if len(grounded) > 3 else ''),
            'grounded_count': len(grounded),
            'template_signals_count': len(template_signals)
        })
    
    return pd.DataFrame(records)

# Dashboard
st.set_page_config(page_title="API Response Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Describe Image - API Response Dashboard")

# Load data
df = load_data()

if df.empty:
    st.warning("No data found in the database")
    st.stop()

# Sidebar Filters
st.sidebar.header("🔍 Filters")

# Score difference filter
st.sidebar.subheader("Score Difference")
min_diff, max_diff_selected = st.sidebar.slider(
    "Filter by score difference range",
    0, 90, (0, 90)
)

# Template filter
template_filter = st.sidebar.radio("Template Detected", ["All", "True", "False"], index=0)
if template_filter == "All":
    template_filter = [True, False]
else:
    template_filter = [template_filter == "True"]

# Repetition filter
repetition_options = df['repetition_severity'].unique().tolist()
repetition_filter = st.sidebar.radio("Repetition Severity", ["All"] + repetition_options, index=0)
if repetition_filter == "All":
    repetition_filter = repetition_options
else:
    repetition_filter = [repetition_filter]

# Grounded count filter
st.sidebar.subheader("Grounded Elements Count")
min_grounded, max_grounded = st.sidebar.slider(
    "Filter by grounded elements count",
    0, 20, (0, 20)
)

# Apply filters
filtered_df = df[
    (df['score_diff'] >= min_diff) & 
    (df['score_diff'] <= max_diff_selected) &
    (df['is_template'].isin(template_filter)) &
    (df['repetition_severity'].isin(repetition_filter)) &
    (df['grounded_count'] >= min_grounded) &
    (df['grounded_count'] <= max_grounded)
]

st.sidebar.metric("Filtered Results", len(filtered_df))

# Metrics
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Responses", len(df))
with col2:
    st.metric("Avg Score", f"{df['score'].mean():.1f}")
with col3:
    st.metric("Avg Expected", f"{df['expected_score'].mean():.1f}")
with col4:
    st.metric("Avg Difference", f"{df['score_diff'].mean():.1f}")
with col5:
    st.metric("Templates", df['is_template'].sum())

# Charts
st.subheader("📈 Score vs Expected Score")
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['score'], mode='lines+markers', name='V0 Score', line=dict(color='#1f77b4')))

# Add V1 scores only for rows that have updated_model_score
filtered_df_with_v1 = filtered_df[filtered_df['updated_score'] != '-'].copy()
if not filtered_df_with_v1.empty:
    filtered_df_with_v1['updated_score_num'] = pd.to_numeric(filtered_df_with_v1['updated_score'])
    fig.add_trace(go.Scatter(x=filtered_df_with_v1.index, y=filtered_df_with_v1['updated_score_num'], mode='lines+markers', name='V1 Score', line=dict(color='#2ca02c')))

fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['expected_score'], mode='lines+markers', name='Expected Score', line=dict(color='#ff7f0e')))
fig.update_layout(height=400, hovermode='x unified')
st.plotly_chart(fig, use_container_width=True)

# Data table
st.subheader("📋 Response Details")

# Column headers
col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([1, 1, 1, 1, 1.5, 1, 1, 1.5, 1])
col1.markdown("**Transcription**")
col2.markdown("**Score**")
col3.markdown("**Updated Score**")
col4.markdown("**Expected**")
col5.markdown("**Remark**")
col6.markdown("**Grounded #**")
col7.markdown("**Template Signals**")
col8.markdown("**Repetition**")
col9.markdown("**Full Response**")
st.divider()

for idx, row in filtered_df.iterrows():
    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([1, 1, 1, 1, 1.5, 1, 1, 1.5, 1])
    
    if col1.button("📝", key=f"trans_{idx}", use_container_width=True):
        st.session_state[f'show_trans_{idx}'] = not st.session_state.get(f'show_trans_{idx}', False)
    
    col2.write(row['score'])
    if row['updated_score'] != '-':
        col3.markdown(f"<div style='color: #2ca02c; font-weight: bold'>{row['updated_score']}</div>", unsafe_allow_html=True)
    else:
        col3.write(row['updated_score'])
    col4.write(row['expected_score'])
    col5.write(row['remark'])
    
    if col6.button(f"📊 {row['grounded_count']}", key=f"btn_{idx}", use_container_width=True):
        st.session_state[f'show_{idx}'] = not st.session_state.get(f'show_{idx}', False)
    
    if row['is_template'] and row['template_signals_count'] > 0:
        if col7.button(f"⚠️ {row['template_signals_count']}", key=f"signals_{idx}", use_container_width=True):
            st.session_state[f'show_signals_{idx}'] = not st.session_state.get(f'show_signals_{idx}', False)
    else:
        col7.markdown("<div style='text-align: center'>❌</div>", unsafe_allow_html=True)
    
    col8.write(row['repetition_severity'])
    
    if col9.button("📜", key=f"full_{idx}", use_container_width=True):
        st.session_state[f'show_full_{idx}'] = not st.session_state.get(f'show_full_{idx}', False)
    
    if st.session_state.get(f'show_{idx}', False):
        col_v0, col_v1 = st.columns(2)
        with col_v0:
            st.markdown(f"**V0 Grounded Elements (Row {idx}):**")
            collection = get_database()
            from bson import ObjectId
            doc = collection.find_one({'_id': ObjectId(row['id'])})
            if doc:
                grounded = doc.get('evaluation_response', {}).get('agent_2_template_detector', {}).get('output', {}).get('evidence', {}).get('grounded_elements_found', [])
                if grounded:
                    for elem in grounded:
                        st.markdown(f"  • {elem}")
                else:
                    st.info("No grounded elements found")
        with col_v1:
            st.markdown(f"**V1 Grounded Elements (Row {idx}):**")
            if doc and doc.get('updated_model_score'):
                grounded_v1 = doc.get('updated_model_score', {}).get('agent_1_content_scorer', {}).get('output', {}).get('evidence', {}).get('grounded_elements_found', [])
                if grounded_v1:
                    for elem in grounded_v1:
                        st.markdown(f"  • {elem}")
                else:
                    st.info("No grounded elements found")
            else:
                st.info("V1 data not available")
    
    if st.session_state.get(f'show_signals_{idx}', False):
        col_v0, col_v1 = st.columns(2)
        with col_v0:
            st.markdown(f"**V0 Template Signals (Row {idx}):**")
            collection = get_database()
            from bson import ObjectId
            doc = collection.find_one({'_id': ObjectId(row['id'])})
            if doc:
                signals = doc.get('evaluation_response', {}).get('agent_2_template_detector', {}).get('output', {}).get('evidence', {}).get('generic_template_signals', [])
                if signals:
                    for signal in signals:
                        st.markdown(f"  • {signal}")
                else:
                    st.info("No template signals found")
        with col_v1:
            st.markdown(f"**V1 Template Signals (Row {idx}):**")
            if doc and doc.get('updated_model_score'):
                signals_v1 = doc.get('updated_model_score', {}).get('agent_1_content_scorer', {}).get('output', {}).get('evidence', {}).get('generic_template_signals', [])
                if signals_v1:
                    for signal in signals_v1:
                        st.markdown(f"  • {signal}")
                else:
                    st.info("No template signals found")
            else:
                st.info("V1 data not available")
    
    if st.session_state.get(f'show_trans_{idx}', False):
        st.markdown(f"**Transcription for Row {idx}:**")
        collection = get_database()
        from bson import ObjectId
        doc = collection.find_one({'_id': ObjectId(row['id'])})
        if doc:
            transcription = doc.get('evaluation_response', {}).get('transcription', '')
            st.text_area("", transcription, height=150, key=f"trans_area_{idx}")
    
    if st.session_state.get(f'show_full_{idx}', False):
        st.markdown(f"**Full API Response for Row {idx}:**")
        collection = get_database()
        from bson import ObjectId
        doc = collection.find_one({'_id': ObjectId(row['id'])})
        if doc:
            doc['_id'] = str(doc['_id'])
            st.json(doc)
    
    st.divider()

# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()
