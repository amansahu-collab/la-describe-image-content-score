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
if 'last_response' not in st.session_state:
    st.session_state.last_response = None

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
                    pte_score = final_result.get('score_out_of_90', 0)
                    is_template = final_result.get('is_template', False)
                    
                    st.session_state.history.append({
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'score': score,
                        'template': is_template
                    })
                    
                    st.session_state.last_response = result
                    
                    st.success("✅ Evaluation completed successfully!")
                    
                    st.divider()
                    col_score1, col_score2 = st.columns([3, 2])
                    
                    with col_score1:
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
                                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 70}
                            }
                        ))
                        fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col_score2:
                        st.metric("PTE Score", f"{pte_score}/90")
                        st.metric("Template", "Detected" if is_template else "None")
                        grounded_elements = agent1.get('evidence', {}).get('grounded_elements_found', [])
                        st.metric("Grounded Elements", len(grounded_elements))
                    
                    # Score breakdown section
                    st.divider()
                    st.subheader("📊 Score Calculation Breakdown")
                    
                    if is_template:
                        st.error("🚫 Template Detected - Score set to 0")
                        st.caption("Response uses generic phrases without specific image details")
                    else:
                        grounded_elements = agent1.get('evidence', {}).get('grounded_elements_found', [])
                        grounded_count = len(grounded_elements)
                        agent2_score = agent2.get('content_relevancy_score', 0)
                        template_signals = agent1.get('evidence', {}).get('generic_template_signals', [])
                        repetition = final_result.get('repetition_analysis', {}) or {}
                        severity = repetition.get('severity', 'none')
                        conclusion_present = agent2.get('conclusion_marker_present', False)
                        
                        if grounded_count == 0:
                            score_range = (10, 10)
                        elif grounded_count == 1:
                            score_range = (11, 29)
                        elif grounded_count == 2:
                            score_range = (30, 49)
                        elif grounded_count == 3:
                            score_range = (50, 59)
                        elif grounded_count == 4:
                            score_range = (60, 69)
                        elif grounded_count in [5, 6]:
                            score_range = (70, 79)
                        elif grounded_count == 7:
                            score_range = (80, 89)
                        else:
                            score_range = (90, 100)
                        
                        range_min, range_max = score_range
                        if range_min == range_max:
                            base_score = range_min
                        else:
                            base_score = range_min + int(agent2_score * 0.10)
                        
                        penalties_map = {"none": 0, "low": 5, "moderate": 8, "high": 15}
                        repetition_penalty = penalties_map.get(severity, 0)
                        template_signal_penalty = len(template_signals) * 2
                        conclusion_adjustment = 5 if conclusion_present else -5
                        
                        col_break1, col_break2, col_break3 = st.columns(3)
                        
                        with col_break1:
                            st.markdown("**🎯 Base Score Components**")
                            st.write(f"• Grounded Elements: {grounded_count}")
                            st.write(f"• Score Range: {range_min}-{range_max}")
                            st.write(f"• Agent 2 Relevancy: {agent2_score}%")
                            st.metric("Base Score", f"{base_score}%", help="Based on grounded elements + relevancy")
                        
                        with col_break2:
                            st.markdown("**➖ Penalties Applied**")
                            st.write(f"• Repetition ({severity}): -{repetition_penalty}%")
                            st.write(f"• Template Signals ({len(template_signals)}): -{template_signal_penalty}%")
                            total_penalty = repetition_penalty + template_signal_penalty
                            st.metric("Total Penalty", f"-{total_penalty}%", delta=f"{severity.title()}", delta_color="inverse")
                        
                        with col_break3:
                            st.markdown("**➕ Adjustments**")
                            if conclusion_present:
                                st.write(f"• Conclusion Present: +5%")
                            else:
                                st.write(f"• No Conclusion: -5%")
                            st.metric("Conclusion", f"{conclusion_adjustment:+d}%", delta="Present" if conclusion_present else "Absent")
                        
                        st.markdown("---")
                        calculation = f"**Final Score = {base_score} (base) - {repetition_penalty} (repetition) - {template_signal_penalty} (template signals) {conclusion_adjustment:+d} (conclusion) = {score}%**"
                        st.markdown(calculation)
                    
                    st.divider()
                    
                    if score >= 70:
                        st.success(f"🎉 Excellent! Score: {score}% - Strong performance")
                    elif score >= 40:
                        st.warning(f"⚠️ Fair. Score: {score}% - Room for improvement")
                    else:
                        st.error(f"❌ Needs Work. Score: {score}% - Significant improvement needed")
                    
                    st.divider()
                    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Feedback", "🔍 Analysis Details", "🔁 Repetition Analysis", "🤖 Agent Details", "📄 Raw Data"])
                    
                    with tab1:
                        st.subheader("Content Feedback")
                        st.write(final_result.get('final_feedback', 'No feedback available'))
                        if is_template:
                            st.warning("**Template Detection Alert**")
                            template_signals = agent1.get('evidence', {}).get('generic_template_signals', [])
                            if template_signals:
                                st.write("Generic phrases detected:")
                                for signal in template_signals:
                                    st.write(f"• \"{signal}\"")
                    
                    with tab2:
                        st.subheader("Detailed Analysis")
                        
                        col_detail1, col_detail2 = st.columns(2)
                        
                        with col_detail1:
                            st.markdown("**✅ Grounded Elements Found**")
                            grounded_elements = agent1.get('evidence', {}).get('grounded_elements_found', [])
                            if grounded_elements:
                                for idx, elem in enumerate(grounded_elements, 1):
                                    st.write(f"{idx}. {elem}")
                            else:
                                st.info("No specific image elements mentioned")
                        
                        with col_detail2:
                            st.markdown("**⚠️ Generic Template Signals**")
                            template_signals = agent1.get('evidence', {}).get('generic_template_signals', [])
                            if template_signals:
                                for idx, signal in enumerate(template_signals, 1):
                                    st.write(f"{idx}. \"{signal}\"")
                            else:
                                st.success("No generic phrases detected")
                        
                        st.markdown("---")
                        st.markdown("**📈 Agent 2 Content Relevancy Analysis**")
                        agent2_score = agent2.get('content_relevancy_score', 0)
                        st.progress(agent2_score / 100)
                        st.write(f"Content Relevancy Score: {agent2_score}%")
                        st.caption("This score measures how well the response describes visually interpretable content from the image")
                    
                    with tab3:
                        repetition = final_result.get('repetition_analysis', {}) or {}
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
                    
                    with tab4:
                        col_agent1, col_agent2 = st.columns(2)
                        with col_agent1:
                            st.subheader("Agent 1: Content Scorer")
                            st.json(agent1)
                        with col_agent2:
                            st.subheader("Agent 2: Template Detector")
                            st.json(agent2)
                    
                    with tab5:
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


if st.session_state.last_response:
    st.divider()
    st.subheader("💬 Add Your Remark")
    with st.form("remark_form"):
        student_remark = st.text_area("Your Remark", placeholder="Share your thoughts on this evaluation...")
        expected_score = st.number_input("Expected Score", min_value=0, max_value=100, value=st.session_state.last_response.get('final_result', {}).get('score', 0))
        submit_remark = st.form_submit_button("Submit Remark", use_container_width=True)
        
        if submit_remark:
            if not student_remark:
                st.error("Please enter a remark")
            else:
                try:
                    remark_response = requests.post(
                        f"{api_url}/remark",
                        headers={"accept": "application/json", "Content-Type": "application/json"},
                        json={
                            "evaluation_response": st.session_state.last_response,
                            "student_remark": student_remark,
                            "expected_score": expected_score,
                            "token": api_token
                        },
                        timeout=10,
                        verify=False
                    )
                    if remark_response.status_code == 200:
                        st.success(f"✅ Remark saved! ID: {remark_response.json().get('id')}")
                    else:
                        st.error(f"Failed to save remark: {remark_response.text}")
                except Exception as e:
                    st.error(f"Error saving remark: {str(e)}")



# Footer
st.divider()
st.caption("💡 Tip: Use the sidebar to view your evaluation history and configure API settings")
