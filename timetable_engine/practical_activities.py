# ============================================================
# OFFICIAL PRACTICAL ACTIVITIES
# TE E&TC - 2024 Pattern
# Semester V
# Source: SPPU TE E&TC 2024 Pattern syllabus
# ============================================================


SEM5_PRACTICAL_ACTIVITIES = {

    # --------------------------------------------------------
    # PCC-304
    # MICROCONTROLLERS & VLSI DESIGN LAB
    # --------------------------------------------------------

    "Microcontrollers & VLSI Design Lab": {

        "Microcontroller": [
            "8051 - Interfacing LEDs",
            "8051 - Multiplexed 7-Segment Display",
            "8051 - Waveform Generation using DAC",
            "8051 - Stepper Motor Interfacing using Timer",
            "8051 - Relay and Buzzer Interfacing",

            "LPC2148 - GLCD Interfacing",
            "LPC2148 - 4x4 Matrix Keyboard Interfacing",
            "LPC2148 - Built-in ADC Programming",
            "LPC2148 - GPS Interfacing",
            "LPC2148 - On-chip RTC Interfacing",
            "LPC2148 - EEPROM using I2C",
            "LPC2148 - SD Card using SPI",

            "Virtual Lab - Additional Experiment 1",
            "Virtual Lab - Additional Experiment 2",
        ],

        "VLSI": [
            "Verilog - 4:1 Multiplexer",
            "Verilog - Full Adder using Two Half Adders",
            "Verilog - 4-bit ALU",
            "Verilog - Binary to Gray Converter",

            "Verilog - JK Flip-Flop and T Flip-Flop",
            "Verilog - 3-bit Asynchronous Counter",
            "Verilog - 3-bit Synchronous Up/Down Counter",
            "Verilog - Johnson/Ring Counter",
            "Verilog - Serial-in Serial-out Shift Register",

            "VLSI Design - Student Selected Group Project",
        ],
    },


    # --------------------------------------------------------
    # PCC-305
    # CELLULAR NETWORK LAB
    # --------------------------------------------------------

    "Cellular Network Lab": [

        "BPSK/QPSK/GMSK Simulation",

        "LTE/5G Path Loss Modelling using MATLAB",

        "5G Ray Tracing Channel Model",

        "RMS Delay Spread Calculation",

        "BER Performance of Multi-Antenna Rayleigh Channel",

        "5G CDL/TDL Channel Model Study",

        "OFDM Frame Error Rate versus SNR",

        "Antenna Spacing for Independent Fading",

        "Channel Coefficient Vector Estimation",

        "Doppler Shift Calculation",

        "Wireless Link Budget Analysis",

        "Cellular Signal Strength KPI Measurement",

        "KPI Monitoring and Traffic Analysis",

        "Interference and Congestion Analysis",

        "Cellular Network TARA / Coverage / Handover Case Study",
    ],


    # --------------------------------------------------------
    # PEC-322
    # PROGRAMME ELECTIVE LAB
    #
    # Current college data:
    # T1/T2 -> Cloud Computing
    # T3     -> Advanced Java Programming
    # --------------------------------------------------------

    "Advanced Java Programming Lab": [

        "ArrayList Student Information Management",

        "Set Interface and PriorityQueue",

        "HashMap Student Database with Comparable and Comparator",

        "Swing Student Result GUI",

        "Swing Mouse Event Handling",

        "JavaFX Form with Property Binding",

        "JSP Employee Information Application",

        "Servlet Calculator",

        "Cookies and HttpSession Login",

        "JDBC Student Database CRUD",

        "Hibernate HQL Queries",

        "Annotation-Based Student Management System",

        "Spring Boot Welcome Application",

        "Spring Boot Student REST API",

        "Spring Boot Student Details with JSON",

        "Advanced Java Mini Project",
    ],


    "Cloud Computing Lab": [

        "GAE Launcher Web Application",

        "CloudSim Scheduling Algorithm",

        "Virtual Machine using OpenStack",

        "File Transfer between Virtual Machines",

        "Virtualization vs Containerization Performance",

        "Traditional vs Elastic Cloud Load Spike Simulation",

        "Google Colab Runtime Telemetry Analysis",

        "AWS S3 / Azure Blob Storage",

        "AWS S3 Backup and Recovery",

        "Virtual Machine Disaster Recovery Strategy",

        "Google Earth Engine Spatiotemporal Analysis",

        "Cloud Spatiotemporal Analysis and Predictive Modelling",

        "Private Cloud / Instance Creation Case Study",

        "Private Cloud Data Storage Security Case Study",

        "Enterprise Cloud Architecture Poster",
    ],


    # --------------------------------------------------------
    # MDM-331
    # MACHINE LEARNING LAB
    # --------------------------------------------------------

    "Machine Learning Lab": [

        "Python and Google Colab Environment Familiarization",

        "Engineering Dataset Visualization",

        "Data Preprocessing and Cleaning",

        "Feature Scaling, Normalization and Standardization",

        "Linear Regression",

        "Logistic Regression Classification",

        "K-Means Clustering",

        "Principal Component Analysis (PCA)",

        "AI APIs and Cloud AI Tools",

        "Machine Learning Mini Project",
    ],


    # --------------------------------------------------------
    # ELC-342
    # TECHNICAL SEMINAR
    # --------------------------------------------------------

    "Technical Seminar": [

        "Topic Finalization and Literature Survey",

        "Research Paper Analysis",

        "Literature Survey Matrix",

        "Synopsis Preparation and Presentation",

        "In-depth Technical Study",

        "Draft Report Preparation",

        "Mock Presentation",

        "Final Seminar Presentation and Viva",
    ],
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_activities(subject):
    """
    Return the official practical activity list
    for the requested subject.
    """

    return SEM5_PRACTICAL_ACTIVITIES.get(subject, [])


def print_activity_database():

    print("=" * 70)
    print("OFFICIAL PRACTICAL ACTIVITY DATABASE")
    print("=" * 70)

    for subject, activities in SEM5_PRACTICAL_ACTIVITIES.items():

        print()
        print(subject)
        print("-" * 70)

        if isinstance(activities, dict):

            for group, items in activities.items():

                print(f"\n{group}")

                for index, activity in enumerate(items, start=1):
                    print(f"  {index}. {activity}")

        else:

            for index, activity in enumerate(activities, start=1):
                print(f"  {index}. {activity}")


if __name__ == "__main__":
    print_activity_database()