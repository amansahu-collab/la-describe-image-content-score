import streamlit as st
import requests
from datetime import datetime
import plotly.graph_objects as go
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Page config
st.set_page_config(
    page_title="Content Evaluator Pro",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", value="https://la-model-proofread.languageacademy.com.au")
    api_token = st.text_input("API Token", value="pte_lsahdpasdhfasdhfasuaosiudfg", type="password")
    
    st.divider()
    st.header("📊 Evaluation History")
    if st.session_state.history:
        for idx, item in enumerate(reversed(st.session_state.history[-5:])):
            with st.expander(f"#{len(st.session_state.history) - idx} - {item['timestamp']}"):
                st.metric("Score", f"{item['score']}%")
                st.caption(f"Template: {'Yes' if item['template'] else 'No'}")
    else:
        st.info("No evaluations yet")
    
    if st.button("Clear History", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# Main content
st.markdown('<h1 class="main-header">📝 Content via Description Evaluator</h1>', unsafe_allow_html=True)
st.markdown("Evaluate student transcriptions against image descriptions with AI-powered analysis")

# Input section
col1, col2 = st.columns(2)

with col1:
    st.subheader("🖼️ Image Description")
    description_input = st.text_area("", height=200, placeholder="Describe what the image contains...", key="desc")

with col2:
    st.subheader("🎤 Student Transcription")
    transcription_input = st.text_area("", height=200, placeholder="Enter what the student said...", key="trans")

# Evaluate button
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    evaluate_btn = st.button("🚀 Evaluate", use_container_width=True, type="primary")

# Evaluation logic
if evaluate_btn:
    if not description_input or not transcription_input:
        st.error("⚠️ Please provide both description and transcription.")
    else:
        with st.spinner("🔄 Analyzing content..."):
            try:
                endpoint = f"{api_url}/content-via-description"
                response = requests.post(
                    endpoint,
                    headers={"accept": "application/json", "Content-Type": "application/json"},
                    json={"image_description": description_input, "transcription": transcription_input, "token": api_token},
                    timeout=30,
                    verify=False
                )
                
                if response.status_code == 200:
                    result = response.json()
                    final_result = result.get('final_result', {})
                    agent1 = result.get('agent_1_content_scorer', {}).get('output', {})
                    agent2 = result.get('agent_2_template_detector', {}).get('output', {})
                    
                    score = final_result.get('score', 0)
                    content_score = agent2.get('content_score_90', 0)  # Actual content score
                    pte_score = final_result.get('score_out_of_90', 0)
                    is_template = agent2.get('template_detected', False)
                    
                    # Add to history
                    st.session_state.history.append({
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'score': score,
                        'template': is_template
                    })
                    
                    st.success("✅ Evaluation completed successfully!")
                    
                    # Score visualization
                    st.divider()
                    col_score1, col_score2, col_score3 = st.columns([2, 1, 1])
                    
                    with col_score1:
                        # Gauge chart
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number+delta",
                            value=score,
                            domain={'x': [0, 1], 'y': [0, 1]},
                            title={'text': "Final Score", 'font': {'size': 24}},
                            gauge={
                                'axis': {'range': [0, 100], 'tickwidth': 1},
                                'bar': {'color': "#667eea"},
                                'steps': [
                                    {'range': [0, 40], 'color': "#fee"},
                                    {'range': [40, 70], 'color': "#ffe"},
                                    {'range': [70, 100], 'color': "#efe"}
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': 70
                                }
                            }
                        ))
                        fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col_score2:
                        st.metric("Content Score", f"{content_score}%")
                        repetition = final_result.get('repetition_analysis', {}) or {}
                        severity = repetition.get('severity', 'none')
                        penalties = {"none": 0, "low": 5, "moderate": 12, "high": 20}
                        penalty = penalties.get(severity, 0)
                        st.metric("Penalty", f"-{penalty}%", delta=f"{severity.title()}")
                    
                    with col_score3:
                        conclusion_present = agent1.get('evidence', {}).get('conclusion_marker_present', False)
                        bonus = 5 if conclusion_present else 0
                        st.metric("Conclusion Bonus", f"+{bonus}%", delta="Present" if conclusion_present else "Absent")
                        st.metric("PTE Score", f"{pte_score}/90")
                        st.metric("Template", "Detected" if is_template else "None")
                    
                    # Performance indicator
                    if score >= 70:
                        st.success(f"🎉 Excellent! Score: {score}% - Strong performance")
                    elif score >= 40:
                        st.warning(f"⚠️ Fair. Score: {score}% - Room for improvement")
                    else:
                        st.error(f"❌ Needs Work. Score: {score}% - Significant improvement needed")
                    
                    # Score breakdown
                    if final_result.get("is_template", False):
                        st.info(f"ℹ️ Template detected → Final score set to {score}% (original content score: {content_score}%)")
                    else:
                        conclusion_present = agent1.get('evidence', {}).get('conclusion_marker_present', False)
                        bonus = 5 if conclusion_present else 0
                        st.info(f"ℹ️ Score calculation: {content_score}% (content) - {penalty}% (penalty) + {bonus}% (bonus) = {score}%")
                    
                    # Detailed analysis tabs
                    st.divider()
                    tab1, tab2, tab3, tab4 = st.tabs(["📋 Feedback", "🔍 Repetition Analysis", "🤖 Agent Details", "📄 Raw Data"])
                    
                    with tab1:
                        st.subheader("Content Feedback")
                        st.write(final_result.get('final_feedback', 'No feedback available'))
                        if is_template:
                            st.warning("**Template Detection Alert**")
                            st.write(agent2.get('feedback', ''))
                    
                    with tab2:
                        if repetition.get('phrase_repetition') or repetition.get('structure_repetition') or repetition.get('connector_overuse'):
                            col_rep1, col_rep2, col_rep3 = st.columns(3)
                            with col_rep1:
                                if repetition.get('phrase_repetition'):
                                    st.markdown("**🔁 Repeated Phrases**")
                                    for item in repetition['phrase_repetition']:
                                        st.write(f"• '{item['phrase']}' ×{item['count']}")
                            with col_rep2:
                                if repetition.get('structure_repetition'):
                                    st.markdown("**📐 Repeated Structures**")
                                    for item in repetition['structure_repetition']:
                                        st.write(f"• {item['pattern']} ×{item['count']}")
                            with col_rep3:
                                if repetition.get('connector_overuse'):
                                    st.markdown("**🔗 Overused Connectors**")
                                    for item in repetition['connector_overuse']:
                                        st.write(f"• '{item['connector']}' ×{item['count']}")
                        else:
                            st.info("No significant repetition detected")
                    
                    with tab3:
                        col_agent1, col_agent2 = st.columns(2)
                        with col_agent1:
                            st.subheader("Agent 1: Content Scorer")
                            st.json(agent1)
                        with col_agent2:
                            st.subheader("Agent 2: Template Detector")
                            st.json(agent2)
                    
                    with tab4:
                        st.json(result)
                
                elif response.status_code == 401:
                    st.error("🔒 Authentication failed. Please check your API token.")
                elif response.status_code == 404:
                    st.error("🔍 API endpoint not found. Please verify the API URL.")
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Please try again.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Connection failed. Please check if the API server is running.")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")

# Footer
st.divider()
st.caption("💡 Tip: Use the sidebar to view your evaluation history and configure API settings")
