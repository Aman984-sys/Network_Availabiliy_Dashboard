import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor
import pandas as pd  # pip install pandas openpyxl
import plotly.express as px  # pip install plotly-express
import streamlit as st  # pip install streamlit
from PIL import Image
from netmiko import ConnectHandler
from datetime import datetime


# Define the login credentials
username = 'user'
password = 'password'

# Get the current date and time
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")


def delete_file(file_path: str) -> None:
    """
    Delete a file if it exists.

    Args:
        file_path (str): The path to the file to delete.
    """
    try:
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")

def check_ping(ip: str) -> bool:
    """
    Check if an IP is pingable.

    Args:
        ip (str): The IP address to check.

    Returns:
        bool: True if the IP is pingable, False otherwise.
    """
    try:
        response = os.system(f"ping {ip}")
        return response == 0
    except Exception as e:
        print(f"Error checking ping for {ip}: {e}")
        return False
        

def update_reachability(row: pd.Series) -> pd.Series:
    """
    Update the reachability status for a given row.

    Args:
        row (pd.Series): The row to update.

    Returns:
        pd.Series: The updated row.
    """
    ups_ip = row['UPS IP']
    olt_ip = row['OLT IP']
    router_ip = row['Router IP']
    switch_ip = row['Switch IP']

    if pd.notna(ups_ip) and ups_ip != "":
        row['UPS Reachability '] = "UPS Reachable" if check_ping(ups_ip) else "UPS Not Reachable"
    else:
        row['UPS Reachability '] = "UPS IP Not Available"

    if pd.notna(olt_ip) and olt_ip != "":
        row['OLT Reachability'] = "OLT Reachable" if check_ping(olt_ip) else "OLT Not Reachable"
    else:
        row['OLT Reachability'] = "OLT IP Not Available"

    if pd.notna(router_ip) and router_ip != "":
        row['Router Reachability'] = "Router Reachable" if check_ping(router_ip) else "Router Not Reachable"
        
        
        if row['Router Reachability'] == "Router Reachable":
        
            device = {
                'device_type': 'cisco_ios',
                'ip': router_ip,
                'username': username,
                'password': password
            }
    
            try:
                net_connect = ConnectHandler(**device)
                net_connect.timeout = 5000
                output = net_connect.send_command("show arp vrf TFIBER-IP-MGMT | include BDI201")
                net_connect.read_timeout = 300
                print(output)
                if output:
                    lines = output.split('\n')
                    line1 = lines[0]
                    row['BDI 201 Configuration Status'] = "Configured"
                    row['Gateway IP Address'] = line1.split()[1]
                    try :
                        line2 = lines[1]
                        row['SNMP MAC Address'] = line2.split()[3]
                    except :
                        row['SNMP MAC Address'] = "Not Found"
                else:
                    row['BDI 201 Configuration Status'] = "Not Configured"
                    #new_df.loc[index, 'Subnet Mask']= 'Not Configured'
                net_connect.disconnect()
            except Exception as e:
                #print(f"Error connecting to {router_ip}: {e}")
                row['BDI 201 Configuration Status'] = "N/A"
                row['Gateway IP Address'] = "N/A"
                row['SNMP MAC Address'] = "N/A"

        else :
            row['BDI 201 Configuration Status'] = "Router Not Reachable"
            row['Gateway IP Address'] = "Router Not Reachable"
            row['SNMP MAC Address'] = "Router Not Reachable"                     

    else:
        row['Router Reachability'] = "Router IP Not Available"
        row['BDI 201 Configuration Status'] = "Router IP Not Available"
        row['Gateway IP Address'] = "Router IP Not Available"
        row['SNMP MAC Address'] = "Router IP Not Available"
        

    if pd.notna(switch_ip) and switch_ip != "":
        row['Switch Reachability'] = "Switch Reachable" if check_ping(switch_ip) else "Switch Not Reachable"
        
        if row['Switch Reachability'] == "Switch Reachable":
            device = {
                'device_type': 'cisco_ios',
                'ip': switch_ip,
                'username': username,
                'password': password
            }
    
            try:
                net_connect = ConnectHandler(**device)
                net_connect.timeout = 5000
                output = net_connect.send_command("show vlan | include 201")
                net_connect.read_timeout = 300
                print(output)
                if output:
                    lines = output.split('\n')
                    line1 = lines[0]
                    row['VLAN 201 Status'] = "Configured"
                    row['VLAN 201 Tagged Port'] = line1.split()[2]
                else:
                    row['VLAN 201 Status'] = "Not Configured"
                    #new_df.loc[index, 'Subnet Mask']= 'Not Configured'
                net_connect.disconnect()
            except Exception as e:
                #print(f"Error connecting to {switch_ip}: {e}")
                row['VLAN 201 Status'] = "N/A"
                row['VLAN 201 Tagged Port'] = "N/A"
                
        else :
            row['VLAN 201 Status'] = "N/A"
            row['VLAN 201 Tagged Port'] = "N/A"
            
    else:
        row['Switch Reachability'] = "Switch IP Not Available"
        row['VLAN 201 Status'] = "Switch IP Not Available"
        row['VLAN 201 Tagged Port'] = "Switch IP Not Available"
        

    return row

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the data by updating the reachability status.

    Args:
        df (pd.DataFrame): The data to process.

    Returns:
        pd.DataFrame: The processed data.
    """
    df['UPS IP'].fillna("", inplace=True)
    df['OLT IP'].fillna("", inplace=True)
    df['Router IP'].fillna("", inplace=True)
    df['Switch IP'].fillna("", inplace=True)

    with ThreadPoolExecutor(max_workers=1000) as executor:
        futures = []
        for index, row in df.iterrows():
            futures.append(executor.submit(update_reachability, row))
        results = [future.result() for future in futures]

    # create a new DataFrame from the results
    df_processed = pd.DataFrame(results)

    return df_processed


def main():
    df = pd.read_excel('PKGA2 UPS NW Details.xlsx',engine='openpyxl')
    #delete_file('your_file.xlsx')
    df = process_data(df)
    df.to_excel('your_file.xlsx',engine='openpyxl',sheet_name=f"Report_{current_datetime}", index=False)
    
    # emojis: https://www.webfx.com/tools/emoji-cheat-sheet/
    st.set_page_config(page_title="UPS IP Reachability Dashboard", page_icon=":bar_chart:", layout="wide")
    logo = Image.open("D:/UPS IP Dashboard/Python/images/company_logo.png")   #insert photo in specified path

    @st.cache
    def UPS_IP_from_excel():
        df_IP = pd.read_excel(
            io="your_file.xlsx",
            engine="openpyxl",
            sheet_name="Sheet1",
            usecols="A:T",
            converters={'LGD Code':str},
            
        )
        return df_IP

    df_UPS_IP = pd.read_excel(
            io="your_file.xlsx",
            engine="openpyxl",
            sheet_name="Sheet1",
            usecols="A:T",
            converters={'LGD Code':str},
            
        )


    with st.container() :
        image_column, text_column = st.columns((1,1))
        with image_column:
            st.image(logo)
        with text_column:
            st.title("UPS IP Reachability Dashboard")
        

    with st.container() :
        st.write("---")
        #left_column = st.columns()
        #with left_column:
        st.subheader("UPS IP Reachability")
        st.dataframe(df_UPS_IP)
    
if __name__ == '__main__':
    main()











