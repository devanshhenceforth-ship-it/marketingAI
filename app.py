import streamlit as st
import requests

# --- Configuration ---
BASE_URL = st.secrets["APP_URL"]
WEBHOOK_URL = st.secrets["N8N_WEBHOOK_EMAIL"]
ST_TITLE = "📧 Outreach Email Reviewer"

st.set_page_config(page_title=ST_TITLE, layout="wide")

# --- API Interaction Layer ---

def get_all_runs():
    """Fetches general lead-generation runs (Tiles). Handles list response."""
    try:
        TILES_URL = BASE_URL.replace('/outreach', '/tiles')
        response = requests.get(f"{TILES_URL}/runs")
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Failed to fetch lead runs: {e}")
        return []

def get_runs():
    """Fetches runs specifically with emails (Outreach)."""
    try:
        response = requests.get(f"{BASE_URL}/emails/runs")
        return response.json().get("runs", [])
    except Exception as e:
        st.error(f"Failed to fetch outreach runs: {e}")
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
        response = requests.get(f"{BASE_URL}/leads/runs/{run_id}", params=params)
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch leads: {e}")
        return None

def update_email_status(email_id, action):
    res = requests.post(f"{BASE_URL}/emails/{email_id}/{action}")
    return res.status_code == 200

def trigger_regeneration(run_id):
    res = requests.post(f"{BASE_URL}/emails/runs/{run_id}/regenerate")
    return res.status_code == 200

def update_run_status(run_id, action):
    res = requests.post(f"{BASE_URL}/emails/runs/{run_id}/{action}")
    return res.status_code == 200

def patch_email_data(email_id, patch_data):
    try:
        res = requests.patch(f"{BASE_URL}/emails/{email_id}", json=patch_data)
        return res.status_code == 200
    except Exception as e:
        st.error(f"Patch failed: {e}")
        return False

def send_run(run_id):
    try:
        res = requests.post(WEBHOOK_URL, json={"run_id": run_id})
        return res.status_code == 200
    except Exception as e:
        st.error(f"Webhook failed: {e}")
        return False

# --- Helper UI Component ---

def render_leads_view(run_id):
    """A dedicated full-page view for leads."""
    if st.button("⬅️ Back to List"):
        if "active_lead_run" in st.session_state:
            del st.session_state.active_lead_run
        st.rerun()
    
    st.title(f"📊 Enriched Leads")
    st.caption(f"Run ID: {run_id}")
    
    leads_data = get_leads(run_id)
    if leads_data and leads_data.get("items"):
        st.write(f"Showing **{len(leads_data['items'])}** enriched leads")
        s1, s2, s3 = st.columns(3)
        s1.metric("Total Leads", leads_data.get("total", 0))
        s2.metric("Page", leads_data.get("page", 1))
        s3.metric("Limit", leads_data.get("limit", 50))
        st.divider()
        for lead in leads_data["items"]:
            with st.expander(f"📍 {lead['title']} - {lead.get('category','Business')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Website:** {lead.get('website')}")
                    st.markdown(f"**Email:** {lead.get('email')}")
                    st.markdown(f"**WhatsApp:** {lead.get('whatsapp_number')}")
                    st.markdown(f"**Address:** `{lead.get('address')}`")
                with col2:
                    st.markdown(f"**Review Count:** {lead.get('review_count',0)}")
                    st.markdown(f"**Review Rating:** ⭐ {lead.get('review_rating',0)}")
                    st.markdown(f"**SEO Score:** {lead.get('seo_score',0)}")
                    st.markdown(f"**Conversion Score:** {lead.get('conversion_score',0)}")
                st.divider()
                st.json(lead)
    else:
        st.info("No lead data found.")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
nav_page = st.sidebar.radio("Select View", ["📧 Email Campaigns", "📂 All Lead Collections"])

# Sync session state to reset drill-down when changing tabs
if "last_nav" not in st.session_state:
    st.session_state.last_nav = nav_page

if st.session_state.last_nav != nav_page:
    if "active_lead_run" in st.session_state:
        del st.session_state.active_lead_run
    st.session_state.last_nav = nav_page

# =========================================================
# PAGE: EMAIL CAMPAIGNS
# =========================================================
if nav_page == "📧 Email Campaigns":
    st.sidebar.divider()
    st.sidebar.header("Campaign Management")

    runs = get_runs()
    current_run_id = None

    if runs:
        run_list = {
            f"{r['run_id'][:8]}... ({r.get('email_count', 0)} emails)": r['run_id']
            for r in runs
        }
        selected_label = st.sidebar.selectbox("Select Campaign Run", options=list(run_list.keys()))
        current_run_id = run_list[selected_label]
    else:
        st.sidebar.warning("No email runs detected.")

    st.sidebar.divider()
    status_filter = st.sidebar.radio("Filter by Status", ["All", "Pending", "Approved", "Declined"])

    st.title(ST_TITLE)

    if current_run_id:
        # --- Action Bar ---
        col_id, col_app, col_dec, col_reg, col_send, col_del = st.columns([3, 1.2, 1.2, 1.2, 1.2, 1])
        with col_id: st.caption(f"Full Run ID: {current_run_id}")
        with col_app:
            if st.button("✅ Approve All", use_container_width=True):
                if update_run_status(current_run_id, "approve"): st.rerun()
        with col_dec:
            if st.button("❌ Decline All", use_container_width=True):
                if update_run_status(current_run_id, "decline"): st.rerun()
        with col_reg:
            if st.button("🔄 Regenerate", use_container_width=True):
                if trigger_regeneration(current_run_id): st.rerun()
        with col_send:
            if st.button("🚀 Send Run", use_container_width=True):
                if send_run(current_run_id): st.success("Run sent!")
        with col_del:
            if st.button("🗑️ Delete Run", use_container_width=True):
                if requests.delete(f"{BASE_URL}/emails/runs/{current_run_id}").status_code == 200: st.rerun()

        # --- Tabs ---
        main_tab_emails, main_tab_leads = st.tabs(["📧 Review Emails", "📊 Enriched Leads"])

        with main_tab_emails:
            data = get_emails(current_run_id, status_filter)
            if data and data.get("items"):
                for item in data["items"]:
                    with st.container(border=True):
                        email_status = item.get("email_status", {})
                        
                        def format_status(s):
                            if not s: return "⚪ pending"
                            status_text = s.get("status", "pending")
                            sent_at = s.get("sent_at")
                            time_str = f" ({sent_at.split('T')[0]} {sent_at.split('T')[1][:5]})" if sent_at else ""
                            if status_text == "sent": return f"🟢 sent{time_str}"
                            if status_text == "failed": return "🔴 failed"
                            return "🟡 pending"

                        h1, h2, h3 = st.columns([4, 1, 2])
                        with h1:
                            st.markdown(f"🏢 {item.get('title', 'Unknown Lead')}")
                            st.caption(f"ID: {item['_id']} | Email: {item.get('lead_email')}")
                        with h2:
                            status = item.get("approval_status", "pending").upper()
                            color = "green" if status == "APPROVED" else "red" if status == "DECLINED" else "orange"
                            st.markdown(f":{color}[**{status}**]")
                        with h3:
                            st.caption(f"Main: {format_status(email_status.get('main'))}  \nF1: {format_status(email_status.get('follow_up_1'))}")

                        tab1, tab2, tab3 = st.tabs(["Main Email", "Follow-ups", "Metadata"])
                        gen_data = item.get("generated_emails", {})

                        with tab1:
                            new_subject = st.text_input("Subject", gen_data.get("main_email_subject", ""), key=f"s_{item['_id']}")
                            mode = st.radio("Mode", ["Preview", "Edit"], key=f"m_{item['_id']}", horizontal=True)
                            if mode == "Preview":
                                st.components.v1.html(gen_data.get("main_email_html", ""), height=350, scrolling=True)
                                new_html_body = gen_data.get("main_email_html", "")
                            else:
                                new_html_body = st.text_area("HTML", gen_data.get("main_email_html", ""), height=350, key=f"e_{item['_id']}")
                        
                        with tab2:
                            col_f1, col_f2, col_f3 = st.columns(3)
                            f1_text = col_f1.text_area("F1", gen_data.get("follow_up_1_body", ""), key=f"f1_{item['_id']}")
                            f2_text = col_f2.text_area("F2", gen_data.get("follow_up_2_body", ""), key=f"f2_{item['_id']}")
                            f3_text = col_f3.text_area("F3", gen_data.get("follow_up_3_body", ""), key=f"f3_{item['_id']}")

                        with tab3:
                            st.json(item.get("metadata", {}))

                        c1, c2, c3, c4, _ = st.columns([1, 1, 1, 1, 3])
                        if c1.button("✅ Approve", key=f"a_{item['_id']}"):
                            if update_email_status(item["_id"], "approve"): st.rerun()
                        if c2.button("❌ Decline", key=f"d_{item['_id']}"):
                            if update_email_status(item["_id"], "decline"): st.rerun()
                        if c3.button("💾 Save", key=f"sa_{item['_id']}"):
                            patch_data = {"generated_emails": {**gen_data, "main_email_subject": new_subject, "main_email_html": new_html_body, "follow_up_1_body": f1_text, "follow_up_2_body": f2_text, "follow_up_3_body": f3_text}}
                            if patch_email_data(item["_id"], patch_data): st.toast("Saved Changes!")
                        if c4.button("🗑️", key=f"del_{item['_id']}"):
                            requests.delete(f"{BASE_URL}/emails/{item['_id']}")
                            st.rerun()
            else:
                st.info("No emails found.")

        with main_tab_leads:
            render_leads_view(current_run_id)
    else:
        st.info("Select a Run ID from the sidebar.")

# =========================================================
# PAGE: ALL LEAD COLLECTIONS
# =========================================================
else:
    if "active_lead_run" in st.session_state:
        render_leads_view(st.session_state.active_lead_run)
    else:
        st.title("📂 All Lead Collections")
        st.markdown("Browse all historical lead data collection runs.")
        
        all_runs = get_all_runs()
        
        if not all_runs:
            st.info("No runs found in the lead collection system.")
        else:
            for r in all_runs:
                run_id = r.get("run_id")
                name = r.get("campaign_name", "Unnamed Campaign")
                city = r.get("city", "Unknown City")
                keywords = ", ".join(r.get("keywords", []))
                status = r.get("status", "unknown").upper()
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1.5])
                    with col1:
                        st.markdown(f"### 🚀 {name}")
                        st.caption(f"Run ID: `{run_id}`")
                        st.markdown(f"**City:** {city.title()} | **Keywords:** `{keywords}`")
                    with col2:
                        st.write(f"**Status:** {status}")
                        st.write(f"**Created:** {r.get('created_at', 'N/A')[:16].replace('T', ' ')}")
                    with col3:
                        if st.button("View Leads", key=f"btn_v_leads_{run_id}", use_container_width=True):
                            st.session_state.active_lead_run = run_id
                            st.rerun()