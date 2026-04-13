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

def get_leads(run_id, page=1, limit=50):
    params = {"page": page, "limit": limit}
    try:
        # Note: Using the specific /leads/ path provided by the user
        response = requests.get(f"{BASE_URL}/leads/runs/{run_id}", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch leads: {e}")
        return None

def update_email_status(email_id, action):
    # action: 'approve' or 'decline'
    res = requests.post(f"{BASE_URL}/emails/{email_id}/{action}")
    return res.status_code == 200

def trigger_regeneration(run_id):
    res = requests.post(f"{BASE_URL}/emails/runs/{run_id}/regenerate")
    return res.status_code == 200

def update_run_status(run_id, action):
    # action: 'approve' or 'decline'
    res = requests.post(f"{BASE_URL}/emails/runs/{run_id}/{action}")
    return res.status_code == 200

def patch_email_data(email_id, patch_data):
    """Partially update an email document."""
    try:
        res = requests.patch(f"{BASE_URL}/emails/{email_id}", json=patch_data)
        return res.status_code == 200
    except Exception as e:
        st.error(f"Patch failed: {e}")
        return False

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
    col_id, col_app, col_dec, col_reg, col_del = st.columns([3, 1.2, 1.2, 1.2, 1])
    with col_id:
        st.caption(f"Full Run ID: {current_run_id}")
    with col_app:
        if st.button("✅ Approve All", type="primary", use_container_width=True, key="app_run"):
            if update_run_status(current_run_id, "approve"):
                st.success("Entire run approved!")
                st.rerun()
    with col_dec:
        if st.button("❌ Decline All", type="secondary", use_container_width=True, key="dec_run"):
            if update_run_status(current_run_id, "decline"):
                st.warning("Entire run declined!")
                st.rerun()
    with col_reg:
        if st.button("🔄 Regenerate", type="secondary", use_container_width=True, key="reg_run"):
            if trigger_regeneration(current_run_id):
                st.success("Regeneration triggered!")
                st.rerun()
    with col_del:
        if st.button("🗑️ Delete Run", type="secondary", use_container_width=True, key="del_run"):
            if requests.delete(f"{BASE_URL}/emails/runs/{current_run_id}").status_code == 200:
                st.rerun()

    # --- Main Tab Menu ---
    main_tab_emails, main_tab_leads = st.tabs(["📧 Review Emails", "📊 Enriched Leads"])

    with main_tab_emails:
        # Data Fetching
        data = get_emails(current_run_id, status_filter)
        
        if data and data.get("items"):
            st.write(f"Showing **{len(data['items'])}** generated emails")
            
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
                        # Subject Lines
                        subjects = gen_data.get("subject_lines", ["No subject generated"])
                        selected_subject = st.selectbox("Suggested Subject Lines", subjects, key=f"sub_{item['_id']}")
                        
                        # Email Body Toggle
                        mode = st.radio("View Mode", ["Preview", "Edit Plain Text"], key=f"mode_{item['_id']}", horizontal=True)
                        if mode == "Preview":
                            st.divider()
                            st.components.v1.html(gen_data.get("main_email_html", ""), height=300, scrolling=True)
                            new_body = gen_data.get("main_email_plain", "")
                        else:
                            new_body = st.text_area("Body (Plain Text)", gen_data.get("main_email_plain", ""), height=300, key=f"edit_body_{item['_id']}")

                    with tab2:
                        col_f1, col_f2, col_f3 = st.columns(3)
                        with col_f1:
                            st.caption("Follow-up 1")
                            f1_text = st.text_area("F1", gen_data.get("follow_up_1", ""), height=200, label_visibility="collapsed", key=f"f1_{item['_id']}")
                        with col_f2:
                            st.caption("Follow-up 2")
                            f2_text = st.text_area("F2", gen_data.get("follow_up_2", ""), height=200, label_visibility="collapsed", key=f"f2_{item['_id']}")
                        with col_f3:
                            st.caption("Follow-up 3")
                            f3_text = st.text_area("F3", gen_data.get("follow_up_3", ""), height=200, label_visibility="collapsed", key=f"f3_{item['_id']}")

                    with tab3:
                        metadata = item.get("metadata", {})
                        st.json({
                            "Place ID": item.get("place_id"),
                            "Website": metadata.get("website"),
                            "Category": metadata.get("category"),
                            "Created At": item.get("created_at")
                        })

                    # Footer Actions
                    act_col1, act_col2, act_col3, act_col4, _ = st.columns([1, 1, 1, 1, 3])
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
                        if st.button("💾 Save", key=f"btn_save_{item['_id']}"):
                            patch_data = {
                                "generated_emails": {
                                    **gen_data,
                                    "main_email_plain": new_body,
                                    "follow_up_1": f1_text,
                                    "follow_up_2": f2_text,
                                    "follow_up_3": f3_text
                                }
                            }
                            if patch_email_data(item['_id'], patch_data):
                                st.toast("Changes saved successfully!")
                                st.rerun()
                    with act_col4:
                        if st.button("🗑️", key=f"btn_del_{item['_id']}"):
                            requests.delete(f"{BASE_URL}/emails/{item['_id']}")
                            st.rerun()
        else:
            st.info("No emails found for the selected criteria.")

    with main_tab_leads:
        leads_data = get_leads(current_run_id)
        if leads_data and leads_data.get("items"):
            st.write(f"Showing **{len(leads_data['items'])}** enriched leads from PostgreSQL")
            
            # Simple Stat Row
            s1, s2, s3 = st.columns(3)
            s1.metric("Total Leads", leads_data.get("total", 0))
            s2.metric("Page", leads_data.get("page", 1))
            s3.metric("Limit", leads_data.get("limit", 50))
            
            st.divider()

            for lead in leads_data["items"]:
                with st.expander(f"📍 {lead['title']} - {lead.get('category', 'Restaurant')}"):
                    l_col1, l_col2 = st.columns(2)
                    with l_col1:
                        st.markdown(f"**Website:** {lead.get('website', 'N/A')}")
                        st.markdown(f"**Email:** {lead.get('email', 'N/A')}")
                        st.markdown(f"**WhatsApp:** {lead.get('whatsapp_number', 'N/A')}")
                        st.markdown(f"**Address:** `{lead.get('address', 'N/A')}`")
                    with l_col2:
                        st.markdown(f"**Review Count:** {lead.get('review_count', 0)}")
                        st.markdown(f"**Review Rating:** ⭐ {lead.get('review_rating', 0)}")
                        st.markdown(f"**SEO Score:** {lead.get('seo_score', 0)}")
                        st.markdown(f"**Conversion Score:** {lead.get('conversion_score', 0)}")
                    
                    st.divider()
                    st.json({
                        "id": lead.get("id"),
                        "place_id": lead.get("place_id"),
                        "tech_stack": lead.get("tech_stack"),
                        "identified_problems": lead.get("identified_problems"),
                        "additional_phone_numbers": lead.get("additional_phone_numbers")
                    })
        else:
            st.info("No lead data found for this run ID.")
else:
    st.info("Select a Run ID from the sidebar to begin reviewing.")