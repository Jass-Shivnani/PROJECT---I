import httpx
import time

q = """In the Unlambda programming language, what exact character or text needs to be added to correct the following code to output "For penguins"? If what is needed is a character, answer with the name of the character. If there are different names for the character, use the shortest. Code:
`r```````````.F.o.r. .p.e.n.g.u.i.n.si

Answer with only the character name."""

t0 = time.time()
with httpx.Client(timeout=45) as client:
    r = client.post("http://127.0.0.1:8900/api/chat", json={"message": q})
    print(f"Status: {r.status_code} in {time.time()-t0:.2f}s")
    print("Response:", r.json().get("response"))
