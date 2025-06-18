import datetime
import sqlite3
import pandas as pd
import streamlit as st
import altair as alt

# Database functions
def init_database():
    """Initialize the SQLite database and create table if it doesn't exist"""
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            issue TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            date_submitted TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_ticket_to_db(ticket_data):
    """Save a ticket to the database"""
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tickets (id, issue, status, priority, date_submitted)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        ticket_data['ID'],
        ticket_data['Issue'],
        ticket_data['Status'],
        ticket_data['Priority'],
        ticket_data['Date Submitted']
    ))
    
    conn.commit()
    conn.close()

def load_tickets_from_db():
    """Load all tickets from the database"""
    conn = sqlite3.connect('tickets.db')
    
    df = pd.read_sql_query('''
        SELECT id as ID, issue as Issue, status as Status, 
               priority as Priority, date_submitted as "Date Submitted"
        FROM tickets 
        ORDER BY created_at DESC
    ''', conn)
    
    conn.close()
    return df

def update_ticket_in_db(ticket_id, status, priority):
    """Update ticket status and priority in database"""
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tickets 
        SET status = ?, priority = ?
        WHERE id = ?
    ''', (status, priority, ticket_id))
    
    conn.commit()
    conn.close()

def get_next_ticket_number():
    """Get the next ticket number from database"""
    conn = sqlite3.connect('tickets.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT MAX(CAST(SUBSTR(id, 8) AS INTEGER)) FROM tickets')
    result = cursor.fetchone()[0]
    
    conn.close()
    
    if result is None:
        return 1001
    else:
        return result + 1

# Initialize database
init_database()

# Show app title and description
st.set_page_config(page_title="Support tickets", page_icon="🎫")
st.title("🎫 Support tickets")
st.write(
    """
    This app shows how you can build an internal tool in Streamlit with database persistence. 
    Here, we are implementing a support ticket workflow. The user can create a ticket, 
    edit existing tickets, and view some statistics.
    """
)

# Load tickets from database
if "df" not in st.session_state or st.button("🔄 Refresh from Database"):
    st.session_state.df = load_tickets_from_db()

# Show a section to add a new ticket
st.header("Add a ticket")

with st.form("add_ticket_form"):
    issue = st.text_area("Describe the issue")
    priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    submitted = st.form_submit_button("Submit")

if submitted:
    if not issue.strip():
        st.error("⚠️ Por favor describe el problema antes de enviar el ticket")
    else:
        # Get next ticket number
        ticket_number = get_next_ticket_number()
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Create ticket data
        ticket_data = {
            "ID": f"TICKET-{ticket_number}",
            "Issue": issue,
            "Status": "Open",
            "Priority": priority,
            "Date Submitted": today,
        }
        
        # Save to database
        try:
            save_ticket_to_db(ticket_data)
            st.success("✅ Ticket guardado en la base de datos!")
            
            # Show ticket details
            df_new = pd.DataFrame([ticket_data])
            st.dataframe(df_new, use_container_width=True, hide_index=True)
            
            # Refresh data from database
            st.session_state.df = load_tickets_from_db()
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error al guardar el ticket: {str(e)}")

# Show section to view and edit existing tickets
st.header("Existing tickets")
st.write(f"Number of tickets: `{len(st.session_state.df)}`")

if len(st.session_state.df) > 0:
    st.info(
        "You can edit the status and priority by double clicking on the cells. "
        "Changes will be saved to the database automatically!",
        icon="✍️",
    )

    # Show the tickets dataframe with st.data_editor
    edited_df = st.data_editor(
        st.session_state.df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                help="Ticket status",
                options=["Open", "In Progress", "Closed"],
                required=True,
            ),
            "Priority": st.column_config.SelectboxColumn(
                "Priority",
                help="Priority",
                options=["High", "Medium", "Low"],
                required=True,
            ),
        },
        disabled=["ID", "Issue", "Date Submitted"],
    )

    # Check for changes and update database
    if not edited_df.equals(st.session_state.df):
        try:
            # Update each changed row in the database
            for idx, row in edited_df.iterrows():
                original_row = st.session_state.df.iloc[idx]
                if (row['Status'] != original_row['Status'] or 
                    row['Priority'] != original_row['Priority']):
                    update_ticket_in_db(row['ID'], row['Status'], row['Priority'])
            
            st.success("✅ Cambios guardados en la base de datos!")
            st.session_state.df = edited_df
            
        except Exception as e:
            st.error(f"❌ Error al actualizar: {str(e)}")

    # Show some metrics and charts
    st.header("Statistics")

    # Show metrics side by side
    col1, col2, col3 = st.columns(3)
    num_open_tickets = len(edited_df[edited_df.Status == "Open"])
    num_in_progress = len(edited_df[edited_df.Status == "In Progress"])
    num_closed = len(edited_df[edited_df.Status == "Closed"])
    
    col1.metric(label="Open tickets", value=num_open_tickets)
    col2.metric(label="In Progress", value=num_in_progress)
    col3.metric(label="Closed tickets", value=num_closed)

    # Show charts
    st.write("##### Ticket status distribution")
    status_plot = (
        alt.Chart(edited_df)
        .mark_bar()
        .encode(
            x="Status:N",
            y="count():Q",
            color="Status:N",
        )
        .properties(height=300)
    )
    st.altair_chart(status_plot, use_container_width=True, theme="streamlit")

    st.write("##### Priority distribution")
    priority_plot = (
        alt.Chart(edited_df)
        .mark_arc()
        .encode(
            theta="count():Q", 
            color="Priority:N"
        )
        .properties(height=300)
    )
    st.altair_chart(priority_plot, use_container_width=True, theme="streamlit")

else:
    st.info("No tickets yet. Create your first ticket above!", icon="🎫")
