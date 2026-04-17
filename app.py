import streamlit as st
import requests
import pycountry
# --- Configuration ---
BASE_URL = st.secrets["APP_URL"]
WEBHOOK_URL = st.secrets["N8N_WEBHOOK_EMAIL"]
WOODPECKER_URL = BASE_URL.replace('/outreach', '/woodpecker')
ST_TITLE = "📧 Outreach Email Reviewer"
ITEMS_PER_PAGE = 20

st.set_page_config(page_title=ST_TITLE, layout="wide")

COUNTRY_LIST = sorted(
    [f"{c.name} ({c.alpha_2})" for c in pycountry.countries],
    key=lambda x: x
)

# --- API Interaction Layer ---

def get_headers():
    if "access_token" in st.session_state:
        return {"Authorization": f"Bearer {st.session_state['access_token']}"}
    return {}

def trigger_job_creation(payload):
    """Triggers the /create-jobs endpoint (New API Integration)"""
    try:
        # Replacing /outreach with /tiles to match your router logic
        TILES_URL = BASE_URL.replace('/outreach', '/tiles')
        print("TILES_URL", TILES_URL, payload)
        res = requests.post(f"{TILES_URL}/create-jobs", json=payload, headers=get_headers())
        return res
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return None

def get_sync_status(run_id):
    """Fetches background synchronization progress for a specific run."""
    try:
        response = requests.get(f"{BASE_URL}/sync-status/{run_id}", headers=get_headers())
        if response.status_code == 200:
            return response.json().get("data", {})
        return None
    except Exception:
        return None

def get_all_runs(page=1):
    try:
        TILES_URL = BASE_URL.replace('/outreach', '/tiles')
        params = {"page": page, "limit": ITEMS_PER_PAGE}
        response = requests.get(f"{TILES_URL}/runs", params=params, headers=get_headers())
        data = response.json()
        if isinstance(data, list):
            return {"items": data, "total": len(data)}
        return data
    except Exception as e:
        st.error(f"Failed to fetch lead runs: {e}")
        return {"items": [], "total": 0}

def get_runs():
    try:
        response = requests.get(f"{BASE_URL}/emails/runs", headers=get_headers())
        return response.json().get("runs", [])
    except Exception as e:
        st.error(f"Failed to fetch outreach runs: {e}")
        return []

def get_emails(run_id, status=None, page=1):
    params = {"limit": ITEMS_PER_PAGE, "page": page}
    if status and status != "All":
        params["approval_status"] = status.lower()
    try:
        response = requests.get(f"{BASE_URL}/emails/runs/{run_id}", params=params, headers=get_headers())
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch emails: {e}")
        return None

def get_leads(run_id, page=1, limit=ITEMS_PER_PAGE):
    params = {"page": page, "limit": limit}
    try:
        response = requests.get(f"{BASE_URL}/leads/runs/{run_id}", params=params, headers=get_headers())
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch leads: {e}")
        return None

def update_email_status(email_id, action):
    return requests.post(f"{BASE_URL}/emails/{email_id}/{action}", headers=get_headers()).status_code == 200

def trigger_regeneration(run_id):
    return requests.post(f"{BASE_URL}/emails/runs/{run_id}/regenerate", headers=get_headers()).status_code == 200

def update_run_status(run_id, action):
    return requests.post(f"{BASE_URL}/emails/runs/{run_id}/{action}", headers=get_headers()).status_code == 200

def patch_email_data(email_id, patch_data):
    try:
        res = requests.patch(f"{BASE_URL}/emails/{email_id}", json=patch_data, headers=get_headers())
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

def get_lead_stats(run_id):
    """Fetches counts (generated, failed, processing) for a specific run."""
    try:
        response = requests.get(f"{BASE_URL}/leads/runs/{run_id}/stats", headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Failed to fetch stats: {e}")
        return None

def update_lead_run_status(run_id, status: str):
    """Updates the overall status of a lead run (e.g., 'completed', 'archived')."""
    try:
        TILES_URL = BASE_URL.replace('/outreach', '/tiles')
        payload = {"status": status}
        res = requests.post(f"{TILES_URL}/runs/{run_id}/status", json=payload, headers=get_headers())
        return res.status_code == 200
    except Exception as e:
        st.error(f"Failed to update run status: {e}")
        return False

# --- Woodpecker API Integration ---
def sync_woodpecker(run_id):
    try:
        res = requests.post(f"{BASE_URL}/emails/runs/{run_id}/sync-woodpecker", headers=get_headers())
        return res.status_code == 200
    except Exception as e:
        st.error(f"Failed to sync woodpecker: {e}")
        return False

def get_woodpecker_mailboxes(force_sync=False):
    try:
        res = requests.get(f"{WOODPECKER_URL}/mailboxes", params={"force_sync": force_sync}, headers=get_headers())
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"Woodpecker Mailboxes Error: {e}")
        return []

def get_woodpecker_campaigns(force_sync=False):
    try:
        res = requests.get(f"{WOODPECKER_URL}/campaigns", params={"force_sync": force_sync}, headers=get_headers())
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        st.error(f"Woodpecker Campaigns Error: {e}")
        return []

def create_woodpecker_campaign(payload):
    try:
        res = requests.post(f"{WOODPECKER_URL}/campaigns", json=payload, headers=get_headers())
        return res.status_code in [200, 201]
    except Exception as e:
        st.error(f"Woodpecker Create Campaign Error: {e}")
        return False

def sync_woodpecker_all():
    try:
        res = requests.post(f"{WOODPECKER_URL}/sync", headers=get_headers())
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        st.error(f"Woodpecker Sync Error: {e}")
        return None

# --- Prompt Management Variables ---
SYSTEM_VARIABLES = ["$category", "$address", "$rag_context"]
USER_VARIABLES = ["$title", "$website", "$business_type", "$tech_stack", "$identified_problems", "$recommended_actions"]

def prompt_editor(label, value="", height=250, key="editor", variables=None):
    st.markdown(f"**{label}**")
    if variables:
        st.caption(f"Available variables: `{', '.join(variables)}`")
    
    return st.text_area(label, value=value, height=height, key=key, label_visibility="collapsed")


def get_prompts():
    try:
        res = requests.get(f"{BASE_URL}/prompts", headers=get_headers())
        if res.status_code == 200:
            return res.json()
        return {"items": [], "total": 0}
    except Exception as e:
        st.error(f"Failed to fetch prompts: {e}")
        return {"items": [], "total": 0}

def upsert_prompt(payload):
    try:
        res = requests.post(f"{BASE_URL}/prompts", json=payload, headers=get_headers())
        return res.status_code == 200
    except Exception as e:
        st.error(f"Failed to save prompt: {e}")
        return False

def delete_prompt(prompt_id):
    try:
        res = requests.delete(f"{BASE_URL}/prompts/{prompt_id}", headers=get_headers())
        return res.status_code == 200
    except Exception as e:
        st.error(f"Failed to delete prompt: {e}")
        return False

def get_resolved_prompt(run_id):
    try:
        res = requests.get(f"{BASE_URL}/resolved-prompt/{run_id}", headers=get_headers())
        if res.status_code == 200:
            return res.json()
        return None
    except Exception as e:
        st.error(f"Failed to resolve prompt: {e}")
        return None

# --- UI Helpers ---

def render_sync_banner(run_id):
    """Optimized Sync Status Banner for Campaign pages."""
    sync = get_sync_status(run_id)
    if not sync: return
    
    is_done = sync.get("is_fully_synced", False)
    status_color = "green" if is_done else "orange"
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 4, 1])
        with c1:
            st.markdown(f"**Pipeline Status:** :{status_color}[{sync.get('status', 'N/A').upper()}]")
            st.caption(f"Campaign: {sync.get('campaign_name', 'N/A')}")
        with c2:
            synced = sync.get("synced_job_ids_count", 0)
            total = sync.get("job_ids_count", 0)
            progress = synced / total if total > 0 else 0
            st.write(f"Processed **{synced}** of **{total}** items")
            st.progress(progress)
        with c3:
            if st.button("🔄 Refresh Status", key=f"sync_btn_{run_id}", use_container_width=True):
                st.rerun()

def render_pagination(key_prefix, current_page, total_items):
    max_pages = (total_items // ITEMS_PER_PAGE) + (1 if total_items % ITEMS_PER_PAGE > 0 else 0)
    if max_pages <= 1:
        return current_page

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Prev", key=f"{key_prefix}_prev", disabled=current_page <= 1):
            return current_page - 1
    with col2:
        st.write(f"Page **{current_page}** of {max_pages} ({total_items} total)")
    with col3:
        if st.button("Next ➡️", key=f"{key_prefix}_next", disabled=current_page >= max_pages):
            return current_page + 1
    return current_page

def render_leads_view(run_id):
    if "lead_page" not in st.session_state:
        st.session_state.lead_page = 1

    # --- Header Navigation & Global Actions ---
    col_nav, col_controls = st.columns([2, 2])

    with col_nav:
        if st.button("⬅️ Back to List", key=f"back_leads_{run_id}"):
            if "active_lead_run" in st.session_state:
                del st.session_state.active_lead_run
            st.session_state.lead_page = 1
            st.rerun()

    with col_controls:
        pipe_col, prompt_col = st.columns(2)

        # -------------------------
        # PIPELINE CONTROL
        # -------------------------
        with pipe_col:
            with st.popover("🚀 Control Pipeline", use_container_width=True):
                st.markdown("### Email Generation Command")

                command = st.radio(
                    "Select Action:",
                    options=["approved", "pending"],
                    format_func=lambda x: "✅ Approve & Start Generation" if x == "approved" else "⏳ Wait / Hold",
                )

                btn_label = "🚀 Start Generation" if command == "approved" else "🛑 Set to Wait"

                if st.button(btn_label, use_container_width=True, type="primary"):
                    if update_lead_run_status(run_id, command):
                        if command == "approved":
                            st.toast(f"Run {run_id} approved! Generation starting...", icon="🚀")
                        else:
                            st.toast(f"Run {run_id} set to wait.", icon="🛑")
                        st.rerun()
                    else:
                        st.error("Failed to update pipeline status.")

        # -------------------------
        # PROMPT EDITOR
        # -------------------------
        with prompt_col:
            with st.popover("🎯 Edit Generation Prompt", use_container_width=True):

                resolved = get_resolved_prompt(run_id)

                if resolved:

                    new_sys = prompt_editor(
                        "System Instruction",
                        value=resolved.get("system_instruction", ""),
                        height=220,
                        key=f"lead_sys_{run_id}",
                        variables=SYSTEM_VARIABLES
                    )

                    new_user = prompt_editor(
                        "User Instruction",
                        value=resolved.get("user_instruction", ""),
                        height=200,
                        key=f"lead_user_{run_id}",
                        variables=USER_VARIABLES
                    )

                    new_rag = st.text_area(
                        "RAG Context",
                        value=resolved.get("rag_context", ""),
                        height=120,
                        key=f"lead_rag_{run_id}"
                    )

                    if st.button("💾 Save Prompt", use_container_width=True):

                        payload = {
                            "run_id": run_id,
                            "system_instruction": new_sys,
                            "user_instruction": new_user,
                            "rag_context": new_rag,
                            "is_universal": False
                        }

                        if upsert_prompt(payload):
                            st.success("Prompt updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update prompt.")

                else:
                    st.warning("No prompt configured yet for this run.")

    st.title("📊 Enriched Leads")

    # --- Stats Section ---
    stats = get_lead_stats(run_id)
    if stats:
        with st.container(border=True):
            cols = st.columns(5)
            cols[0].metric("Total Leads", stats.get("total", 0))
            cols[1].metric("Generated Emails", stats.get("generated", 0))
            cols[2].metric("Processing", stats.get("processing", 0))
            cols[3].metric("Pending", stats.get("pending", 0))
            cols[4].metric("Failed", stats.get("failed", 0), delta_color="inverse")

    st.caption(f"Run ID: {run_id}")

    # -------------------------
    # LEADS TABLE
    # -------------------------
    leads_data = get_leads(run_id, page=st.session_state.lead_page)

    if leads_data and leads_data.get("items"):

        new_page = render_pagination(
            "leads",
            st.session_state.lead_page,
            leads_data.get("total", 0)
        )

        if new_page != st.session_state.lead_page:
            st.session_state.lead_page = new_page
            st.rerun()

        st.divider()

        for lead in leads_data["items"]:

            with st.container(border=True):

                header_col, status_col = st.columns([3, 1])

                with header_col:
                    st.markdown(f"#### 📍 {lead.get('title', 'Unknown')}")

                with status_col:

                    if lead.get("is_email_generated"):
                        st.success("✉️ Email Generated")

                    elif lead.get("email_generation_status") == "processing":
                        st.warning("⏳ Processing")

                    elif lead.get("email_generation_status") == "failed":
                        st.error("❌ Failed")

                    else:
                        st.info("🌑 Pending Email Generation")

                col1, col2 = st.columns([2, 1])

                with col1:
                    st.caption(f"Category: {lead.get('category','Business')}")
                    st.markdown(f"**Website:** {lead.get('website')}")
                    st.markdown(f"**Email:** {lead.get('email')}")
                    st.markdown(f"**Address:** `{lead.get('address')}`")

                with col2:
                    st.metric("SEO Score", lead.get('seo_score', 0))
                    st.metric("Rating", f"⭐ {lead.get('review_rating', 0)}")

                with st.expander("View Raw JSON Data"):
                    st.json(lead)

    else:
        st.info("No lead data found.")

# --- Authentication & Login Flow ---
if "access_token" not in st.session_state:
    st.title("🔒 Login Required")
    with st.container(border=True):
        st.subheader("Please sign in to continue")
        with st.form("login_form"):
            username = st.text_input("Username", value="omji@henceforth.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            if submit:
                # Based on the user instruction making a form data request
                payload = {
                    "username": username,
                    "password": password,
                    "grant_type": "password"
                }
                AUTH_URL = BASE_URL.replace('/outreach', '/auth/login')
                try:
                    res = requests.post(AUTH_URL, data=payload)
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state["access_token"] = data.get("access_token")
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your credentials.")
                except Exception as e:
                    st.error(f"Login request failed: {e}")
    st.stop()  # Stop execution of the rest of the app until logged in

# --- Sidebar Navigation ---
st.sidebar.title("🚀 Navigation")
nav_page = st.sidebar.radio("Select View", ["📧 Email Campaigns", "📂 Lead Collections", "🎯 Prompt Management", "🦜 Woodpecker Management"])

if "last_nav" not in st.session_state or st.session_state.last_nav != nav_page:
    st.session_state.email_page = 1
    st.session_state.lead_page = 1
    st.session_state.coll_page = 1
    if "active_lead_run" in st.session_state:
        del st.session_state.active_lead_run
    st.session_state.last_nav = nav_page

# =========================================================
# PAGE: EMAIL CAMPAIGNS
# =========================================================
if nav_page == "📧 Email Campaigns":
    if "email_page" not in st.session_state:
        st.session_state.email_page = 1

    runs = get_runs()
    current_run_id = None

    if runs:
        run_list = {f"{r['run_id'][:8]}... ({r.get('email_count', 0)} emails)": r['run_id'] for r in runs}
        selected_label = st.sidebar.selectbox("Select Campaign Run", options=list(run_list.keys()))
        current_run_id = run_list[selected_label]
        
        if "last_run_id" not in st.session_state or st.session_state.last_run_id != current_run_id:
            st.session_state.email_page = 1
            st.session_state.last_run_id = current_run_id
    else:
        st.sidebar.warning("No email runs detected.")

    st.sidebar.divider()
    status_filter = st.sidebar.radio("Filter by Status", ["All", "Pending", "Approved", "Declined"])

    st.title(ST_TITLE)

    if current_run_id:
        render_sync_banner(current_run_id)

        col_app, col_dec, col_reg, col_send, col_woodpecker, col_del = st.columns([1, 1, 1, 1, 1, 1])
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
            if st.button("🚀 Push to n8n", use_container_width=True): 
                if send_run(current_run_id): st.success("Run sent!")
        with col_woodpecker:
            if st.button("🦜 Sync Woodpecker", use_container_width=True):
                if sync_woodpecker(current_run_id): st.success("Woodpecker sync initiated!")
        with col_del: 
            if st.button("🗑️ Delete", type="primary", use_container_width=True): 
                if requests.delete(f"{BASE_URL}/emails/runs/{current_run_id}", headers=get_headers()).status_code == 200: st.rerun()
        
        st.caption(f"Full Run ID: `{current_run_id}`")

        # --- Quick Prompt Configuration ---
        with st.expander("🎯 Campaign Prompt Settings"):
            st.info("Customize variables for this specific campaign run.")
            resolved = get_resolved_prompt(current_run_id)
            if resolved:
                c1, c2 = st.columns(2)
                with c1:
                    new_sys = prompt_editor("System Instruction", value=resolved.get("system_instruction", ""), height=250, key=f"camp_sys_{current_run_id}", variables=SYSTEM_VARIABLES)
                with c2:
                    new_user = prompt_editor("User Instruction", value=resolved.get("user_instruction", ""), height=250, key=f"camp_user_{current_run_id}", variables=USER_VARIABLES)
                
                new_rag = st.text_area("RAG Context", value=resolved.get("rag_context", ""), height=100, key=f"camp_rag_{current_run_id}")
                
                if st.button("💾 Save Campaign Prompts", use_container_width=True, type="primary"):
                    p_payload = {
                        "run_id": current_run_id,
                        "system_instruction": new_sys,
                        "user_instruction": new_user,
                        "rag_context": new_rag,
                        "is_universal": False
                    }
                    if upsert_prompt(p_payload):
                        st.success("Campaign prompts updated!")
                        st.rerun()

        main_tab_emails, main_tab_leads = st.tabs(["📧 Review Emails", "📊 Enriched Leads"])

        with main_tab_emails:
            data = get_emails(current_run_id, status_filter, page=st.session_state.email_page)
            if data and data.get("items"):
                st.session_state.email_page = render_pagination("emails", st.session_state.email_page, data.get("total", 0))

                for item in data["items"]:
                    with st.container(border=True):
                        email_status = item.get("email_status", {})
                        
                        def format_status(s):
                            if not s: return "⚪ pending"
                            st_text = s.get("status", "pending")
                            sent_at = s.get("sent_at")
                            time_str = f" ({sent_at.split('T')[0]})" if sent_at else ""
                            if st_text == "sent": return f"🟢 sent{time_str}"
                            if st_text == "failed": return "🔴 failed"
                            return "🟡 pending"

                        h1, h2, h3 = st.columns([4, 1.5, 2.5])
                        with h1:
                            st.markdown(f"#### 🏢 {item.get('title', 'Unknown Lead')}")
                            st.caption(f"ID: {item['_id']} | {item.get('lead_email')}")
                        with h2:
                            app_status = item.get("approval_status", "pending").upper()
                            color = "green" if app_status == "APPROVED" else "red" if app_status == "DECLINED" else "orange"
                            st.markdown(f":{color}[**{app_status}**]")
                        with h3:
                            st.caption(f"Main: {format_status(email_status.get('main'))}")
                            st.caption(f"F1: {format_status(email_status.get('follow_up_1'))}")

                        tab1, tab2, tab3 = st.tabs(["Draft Editor", "Follow-ups", "Technical Data"])
                        gen_data = item.get("generated_emails", {})

                        with tab1:
                            new_subject = st.text_input("Subject", gen_data.get("main_email_subject", ""), key=f"s_{item['_id']}")
                            mode = st.radio("View", ["Preview", "Edit HTML"], key=f"m_{item['_id']}", horizontal=True)
                            if mode == "Preview":
                                st.components.v1.html(gen_data.get("main_email_html", ""), height=300, scrolling=True)
                                new_html_body = gen_data.get("main_email_html", "")
                            else:
                                new_html_body = st.text_area("HTML Source", gen_data.get("main_email_html", ""), height=300, key=f"e_{item['_id']}")
                        
                        with tab2:
                            c_f1, c_f2, c_f3 = st.columns(3)
                            f1_text = c_f1.text_area(gen_data.get("follow_up_1_subject","Follow-Up-1"), gen_data.get("follow_up_1_body", ""), key=f"f1_{item['_id']}", height=200)
                            f2_text = c_f2.text_area(gen_data.get("follow_up_2_subject","Follow-Up-2"), gen_data.get("follow_up_2_body", ""), key=f"f2_{item['_id']}", height=200)
                            f3_text = c_f3.text_area(gen_data.get("follow_up_3_subject","Follow-Up-3"), gen_data.get("follow_up_3_body", ""), key=f"f3_{item['_id']}", height=200)
                        with tab3:
                            st.json(item)

                        c1, c2, c3, c4, _ = st.columns([1, 1, 1, 1, 4])
                        if c1.button("✅ Approve", key=f"a_{item['_id']}"):
                            if update_email_status(item["_id"], "approve"): st.rerun()
                        if c2.button("❌ Decline", key=f"d_{item['_id']}"):
                            if update_email_status(item["_id"], "decline"): st.rerun()
                        if c3.button("💾 Save", key=f"sa_{item['_id']}"):
                            patch_data = {"generated_emails": {**gen_data, "main_email_subject": new_subject, "main_email_html": new_html_body, "follow_up_1_body": f1_text, "follow_up_2_body": f2_text}}
                            if patch_email_data(item["_id"], patch_data): st.toast("Saved Changes!")
                        if c4.button("🗑️", key=f"del_{item['_id']}", type="secondary"):
                            requests.delete(f"{BASE_URL}/emails/{item['_id']}", headers=get_headers())
                            st.rerun()
            else:
                st.info("No emails matching the current filter.")

        with main_tab_leads:
            render_leads_view(current_run_id)

# =========================================================
# PAGE: LEAD COLLECTIONS (OPTIMIZED)
# =========================================================
elif nav_page == "📂 Lead Collections":
    if "active_lead_run" in st.session_state:
        render_leads_view(st.session_state.active_lead_run)
    else:
        st.title("📂 Collection Management")
        
        tab_list, tab_create = st.tabs(["📋 View All Collections", "🆕 Start New Collection"])

        with tab_create:
            st.subheader("Trigger New Lead Scraper Job")
            with st.form("create_job_form"):
                col1, col2 = st.columns(2)
                with col1:
                    campaign_name = st.text_input("Campaign Name", placeholder="Dublin_Dentists_Q2")
                    
                    # --- Searchable Country Selectbox ---
                    selected_country_entry = st.selectbox(
                        "Country", 
                        options=COUNTRY_LIST, 
                        index=COUNTRY_LIST.index("Ireland (IE)") if "Ireland (IE)" in COUNTRY_LIST else 0,
                        help="Search for a country. Mapped with ISO alpha-2 codes."
                    )
                    # Extract pure country name (before the parenthesis) for the API
                    country_name = selected_country_entry.split(" (")[0]
                    # Extract ISO code (inside the parenthesis)
                    country_iso = selected_country_entry.split("(")[-1].strip(")")

                    city = st.text_input("City", placeholder="Dublin")
                    keywords = st.text_area("Keywords (one per line)", placeholder="Dentist\nDental Clinic")
                with col2:
                    zoom = st.number_input("Zoom Level", value=15)
                    radius = st.number_input("Radius (meters)", value=500)
                
                with st.expander("Advanced Configuration"):
                    ca, cb = st.columns(2)
                    step = ca.number_input("Step", value=3)
                    depth = cb.number_input("Depth", value=10)
                    email_scraping = st.toggle("Enable Email Scraping", value=True)
                    fast_mode = st.toggle("Fast Mode", value=False)
                    proxies = st.text_area("Proxies (Optional, one per line)")

                submit = st.form_submit_button("🚀 Start Collection", use_container_width=True)

                if submit:
                    if not campaign_name or not city or not keywords:
                        st.error("Campaign Name, City, and Keywords are required.")
                    else:
                        payload = {
                            "city": city,
                            "country": country_iso.lower(),
                            # "country_code": country_iso, # Optional: pass ISO if backend supports it
                            "keywords": [k.strip() for k in keywords.split("\n") if k.strip()],
                            "campaign_name": campaign_name,
                            "zoom": int(zoom),
                            "step": int(step),
                            "radius": int(radius),
                            "depth": int(depth),
                            "email": email_scraping,
                            "fast_mode": fast_mode,
                            "proxies": [p.strip() for p in proxies.split("\n") if p.strip()]
                        }
                        
                        with st.spinner("Initializing Pipeline..."):
                            response = trigger_job_creation(payload)
                            if response and response.status_code == 200:
                                st.success(f"Job successfully created! Run ID: {response.json().get('run_id')}")
                                st.rerun()
                            else:
                                err = response.json().get('detail') if response else "Unknown Connection Error"
                                st.error(f"Failed to start job: {err}")

        with tab_list:
            if "coll_page" not in st.session_state:
                st.session_state.coll_page = 1

            runs_data = get_all_runs(page=st.session_state.coll_page)
            total_runs = runs_data.get("total", 0)
            
            if not runs_data.get("items"):
                st.info("No pipeline data found.")
            else:
                st.session_state.coll_page = render_pagination("coll", st.session_state.coll_page, total_runs)

                for r in runs_data["items"]:
                    run_id = r.get("run_id")
                    sync = get_sync_status(run_id)
                    
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.markdown(f"### 🚀 {r.get('campaign_name', 'Unnamed Collection')}")
                            st.caption(f"ID: `{run_id}`")
                        with col2:
                            if sync:
                                synced = sync.get("synced_job_ids_count", 0)
                                total = sync.get("job_ids_count", 0)
                                st.write(f"**Sync Progress:** {synced}/{total}")
                                st.progress(synced / total if total > 0 else 0)
                            else:
                                st.write(f"**Status:** {r.get('status', 'unknown').upper()}")
                        with col3:
                            if st.button("Browse Leads", key=f"btn_v_leads_{run_id}", use_container_width=True):
                                st.session_state.active_lead_run = run_id
                                st.session_state.lead_page = 1
                                st.rerun()

# =========================================================
# PAGE: PROMPT MANAGEMENT
# =========================================================

elif nav_page == "🎯 Prompt Management":
    st.title("🎯 Prompt Management")
    st.caption("Manage AI templates used to generate outreach emails.")

    tab_upsert, = st.tabs(["🆕 Create / Update Prompt"])
    with tab_upsert:

        st.subheader("Create New Prompt")

        template = st.selectbox("Load Template", ["None"])

        u_run_id = st.text_input("Run ID (Optional)")

        u_sys = prompt_editor(
            "System Instruction",
            value=st.session_state.get("system_prompt_create", ""),
            key="system_prompt_create",
            height=260,
            variables=SYSTEM_VARIABLES
        )

        u_user = prompt_editor(
            "User Instruction",
            value="",
            key="user_prompt_create",
            height=200,
            variables=USER_VARIABLES
        )

        u_rag = prompt_editor(
            "RAG Context",
            value="",
            key="rag_prompt_create",
            height=150
        )

        u_universal = st.checkbox("Universal Prompt")

        if st.button("💾 Save Prompt", use_container_width=True):

            if not u_sys:
                st.error("System prompt required")
            else:

                payload = {
                    "run_id": u_run_id if u_run_id else None,
                    "system_instruction": u_sys,
                    "user_instruction": u_user,
                    "rag_context": u_rag,
                    "is_universal": u_universal
                }

                if upsert_prompt(payload):
                    st.success("Prompt saved")
                    st.rerun()

# =========================================================
# PAGE: WOODPECKER MANAGEMENT
# =========================================================
elif nav_page == "🦜 Woodpecker Management":
    st.title("🦜 Woodpecker Management")
    st.caption("Manage your Woodpecker mailboxes, campaigns, and sync status.")

    tab_mailboxes, tab_campaigns, tab_sync = st.tabs(["📬 Mailboxes", "📣 Campaigns", "🔄 Sync"])

    # ──────────────────────────────────────────────
    # TAB: Mailboxes
    # ──────────────────────────────────────────────
    with tab_mailboxes:
        col_hdr, col_refresh = st.columns([4, 1])
        with col_hdr:
            st.subheader("Connected Mailboxes")
        with col_refresh:
            force_sync_mb = st.button("🔄 Force Sync", key="wp_mb_sync", use_container_width=True)

        mailboxes = get_woodpecker_mailboxes(force_sync=force_sync_mb)

        if mailboxes:
            for mb in mailboxes:
                details = mb.get("details", {})
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**📧 {details.get('email', 'Unknown')}**")
                        st.caption(f"ID: `{mb.get('id', 'N/A')}` | Provider: {details.get('provider', 'N/A')}")
                    with c2:
                        status = mb.get("status", "unknown")
                        color = "green" if status == "active" else "orange"
                        st.markdown(f":{color}[**{status.upper()}**]")
                        st.caption(f"Limit: {details.get('daily_limit', 0)}/day")
        else:
            st.info("No mailboxes found. Click 'Force Sync' to pull from Woodpecker.")

    # ──────────────────────────────────────────────
    # TAB: Campaigns
    # ──────────────────────────────────────────────
    with tab_campaigns:
        col_hdr2, col_refresh2 = st.columns([4, 1])
        with col_hdr2:
            st.subheader("Woodpecker Campaigns")
        with col_refresh2:
            force_sync_cp = st.button("🔄 Force Sync", key="wp_cp_sync", use_container_width=True)

        campaigns = get_woodpecker_campaigns(force_sync=force_sync_cp)

        if campaigns:
            for cp in campaigns:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"### 📣 {cp.get('name', 'Unnamed Campaign')}")
                        st.caption(f"ID: `{cp.get('id', 'N/A')}`")
                    with c2:
                        status = cp.get("status", "unknown")
                        color = "green" if status in ["running", "active", "RUNNING"] else "orange" if status in ["draft", "DRAFT"] else "red"
                        st.markdown(f":{color}[**{status.upper()}**]")
                    with c3:
                        per_day = cp.get("per_day", 0)
                        st.metric("Per Day", per_day)
                    with st.expander("View Raw Data"):
                        st.json(cp)
        else:
            st.info("No campaigns found. Click 'Force Sync' to pull from Woodpecker.")

        st.divider()
        st.subheader("Create New Campaign")
        
        mailboxes_for_campaign = get_woodpecker_mailboxes(force_sync=False)
        mailbox_options = {f"{m.get('details', {}).get('email')} (ID: {m.get('id')})": m.get("id") for m in mailboxes_for_campaign if m.get("id")}
        
        with st.form("wp_create_campaign_form"):
            cp_name = st.text_input("Campaign Name", placeholder="Q2 Outreach - Dentists")
            selected_mailboxes = st.multiselect("Select Delivery Mailboxes", options=list(mailbox_options.keys()))
            cp_submit = st.form_submit_button("🚀 Create Campaign", use_container_width=True)
            
            if cp_submit:
                if not cp_name or not selected_mailboxes:
                    st.error("Campaign name and at least one mailbox are required.")
                else:
                    payload = {
                        "name": cp_name,
                        "email_account_ids": [mailbox_options[k] for k in selected_mailboxes]
                    }
                    if create_woodpecker_campaign(payload):
                        st.success(f"Campaign '{cp_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create campaign.")

    # ──────────────────────────────────────────────
    # TAB: Full Sync
    # ──────────────────────────────────────────────
    with tab_sync:
        st.subheader("Full Resync")
        st.info("Trigger a full resync of all mailboxes and campaigns from Woodpecker.")
        if st.button("🔄 Sync Everything", use_container_width=True, type="primary"):
            with st.spinner("Syncing with Woodpecker..."):
                sync_result = sync_woodpecker_all()
                if sync_result and sync_result.get("success"):
                    st.success(f"Sync complete! Retrieved {sync_result.get('mailboxes_synced', 0)} mailboxes and {sync_result.get('campaigns_synced', 0)} campaigns.")
                    st.rerun()
                else:
                    err_msg = sync_result.get("message", "Unknown error") if sync_result else "Please try again."
                    st.error(f"Sync failed: {err_msg}")