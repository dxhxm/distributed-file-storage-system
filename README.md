# Distributed Fault-Tolerant File Storage System

## Team Members

| Name                | Registration Number | Email                  |
| ------------------- | ------------------- | ---------------------- |
| Jayakody J.A.D.D.S. | IT24610791          | it24610791@my.sliit.lk |
| Weeramanthri R.D.   | IT24610795          | it24610795@my.sliit.lk |
| Pramodini A.G.H.    | IT24610786          | it24610786@my.sliit.lk |
| Rupasinghe R.A.C.A. | IT24610794          | it24610794@my.sliit.lk |

---

## Instructions to Run the Prototype

### 1. Clone the Repository

```bash
git clone <github-repository-link>
cd distributed-file-storage-system
```

---

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate the environment.

Mac / Linux

```bash
source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Start the Distributed Nodes

Run each node in a separate terminal.

Start Node A

```bash
python nodes/nodeA.py
```

Start Node B

```bash
python nodes/nodeB.py
```

Start Node C

```bash
python nodes/nodeC.py
```

---

### 5. Access the API

After starting the servers, open the FastAPI documentation:

```
http://localhost:8000/docs
```

This interface can be used to test the available API endpoints such as uploading and retrieving files.

---

## Notes

* The system simulates a **distributed file storage system** using multiple nodes running on different ports.
* Each node represents a server in the distributed environment.
