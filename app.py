import streamlit as st
import requests
# --- Configuration ---
BASE_URL = st.secrets["APP_URL"]
ST_TITLE = "📧 Outreach Email Reviewer"

st.set_page_config(page_title=ST_TITLE, layout="wide")

# --- API Interaction Layer ---
def get_runs():
    try:
        response = requests.get(f"{BASE_URL}/emails/runs")
        return response.json().get("runs", [])
    except Exception as e:
        st.error(f"Failed to fetch runs: {e}")
        return []

def get_emails(run_id, status=None):
    params = {"limit": 50}
    if status and status != "All":
        params["approval_status"] = status.lower()
    try:
        response = requests.get(f"{BASE_URL}/emails/runs/{run_id}", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch emails: {e}")
        return None

def update_email_status(email_id, action):
    # action: 'approve' or 'decline'
    res = requests.post(f"{BASE_URL}/emails/{email_id}/{action}")
    return res.status_code == 200

def trigger_regeneration(run_id):
    res = requests.post(f"{BASE_URL}/emails/runs/{run_id}/regenerate")
    return res.status_code == 200

# --- Sidebar ---
st.sidebar.header("Campaign Management")
runs = get_runs()

if runs:
    # Formatting run list for the dropdown
    run_list = {f"{r['run_id'][:8]}... ({r['email_count']} emails)": r['run_id'] for r in runs}
    selected_label = st.sidebar.selectbox("Select Campaign Run", options=list(run_list.keys()))
    current_run_id = run_list[selected_label]
else:
    st.sidebar.warning("No runs detected.")
    current_run_id = None

st.sidebar.divider()
status_filter = st.sidebar.radio("Filter by Status", ["All", "Pending", "Approved", "Declined"])

# --- Main Content ---
st.title(ST_TITLE)

if current_run_id:
    # Action Bar
    col_a, col_b, col_c = st.columns([3, 1, 1])
    with col_a:
        st.caption(f"Full Run ID: {current_run_id}")
    with col_b:
        if st.button("🔄 Regenerate Run", type="secondary", use_container_width=True):
            if trigger_regeneration(current_run_id):
                st.success("Regeneration triggered!")
                st.rerun()
    with col_c:
        if st.button("🗑️ Delete Run", type="primary", use_container_width=True):
            requests.delete(f"{BASE_URL}/emails/runs/{current_run_id}")
            st.rerun()

    # Data Fetching
    data = get_emails(current_run_id, status_filter)
    
    if data and data.get("items"):
        st.write(f"Showing **{len(data['items'])}** results")
        
        for item in data["items"]:
            with st.container(border=True):
                # Header info
                h_col1, h_col2 = st.columns([4, 1])
                with h_col1:
                    st.markdown(f"🏢 {item.get('title', 'Unknown Lead')}")
                    st.caption(f"ID: {item['_id']} | Email: {item.get('lead_email')}")
                with h_col2:
                    status = item.get('approval_status', 'pending').upper()
                    color = "green" if status == "APPROVED" else "red" if status == "DECLINED" else "orange"
                    st.markdown(f":{color}[**{status}**]")

                # Content Tabs
                tab1, tab2, tab3 = st.tabs(["Main Email", "Follow-ups", "Metadata"])
                
                gen_data = item.get("generated_emails", {})
                
                with tab1:
                    # Subject Line Dropdown (since there are multiple)
                    subjects = gen_data.get("subject_lines", ["No subject generated"])
                    st.selectbox("Suggested Subject Lines", subjects, key=f"sub_{item['_id']}")
                    
                    # Email Body Toggle
                    mode = st.radio("View Mode", ["Preview", "Plain Text"], key=f"mode_{item['_id']}", horizontal=True)
                    if mode == "Preview":
                        st.divider()
                        st.components.v1.html(gen_data.get("main_email_html", ""), height=300, scrolling=True)
                    else:
                        st.text_area("Plain Text", gen_data.get("main_email_plain", ""), height=250)

                with tab2:
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        st.caption("Follow-up 1")
                        st.text_area("F1", gen_data.get("follow_up_1", ""), height=200, label_visibility="collapsed", key=f"f1_{item['_id']}")
                    with col_f2:
                        st.caption("Follow-up 2")
                        st.text_area("F2", gen_data.get("follow_up_2", ""), height=200, label_visibility="collapsed", key=f"f2_{item['_id']}")
                    with col_f3:
                        st.caption("Follow-up 3")
                        st.text_area("F3", gen_data.get("follow_up_3", ""), height=200, label_visibility="collapsed", key=f"f3_{item['_id']}")

                with tab3:
                    metadata = item.get("metadata", {})
                    st.json({
                        "Place ID": item.get("place_id"),
                        "Website": metadata.get("website"),
                        "Category": metadata.get("category"),
                        "Created At": item.get("created_at")
                    })

                # Footer Actions
                act_col1, act_col2, act_col3, _ = st.columns([1, 1, 1, 4])
                with act_col1:
                    if st.button("✅ Approve", key=f"btn_app_{item['_id']}"):
                        if update_email_status(item['_id'], "approve"):
                            st.toast(f"Approved {item.get('title')}")
                            st.rerun()
                with act_col2:
                    if st.button("❌ Decline", key=f"btn_dec_{item['_id']}"):
                        if update_email_status(item['_id'], "decline"):
                            st.toast(f"Declined {item.get('title')}")
                            st.rerun()
                with act_col3:
                    if st.button("🗑️ Delete", key=f"btn_del_{item['_id']}"):
                        requests.delete(f"{BASE_URL}/emails/{item['_id']}")
                        st.rerun()
    else:
        st.info("No emails found for the selected criteria.")
else:
    st.info("Select a Run ID from the sidebar to begin reviewing.")