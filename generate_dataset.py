import pandas as pd
import random

data = []

for _ in range(1000):

    # Decide if user is fake or real
    label = random.choice([0, 1])  # 0 = real, 1 = fake

    if label == 0:
        # REAL USER behavior
        posts = random.randint(5, 100)
        followers = random.randint(50, 1000)
        following = random.randint(30, 800)
        login_freq = random.randint(1, 5)
        account_age = random.randint(100, 2000)

    else:
        # FAKE USER behavior
        posts = random.randint(0, 10)
        followers = random.randint(0, 50)
        following = random.randint(200, 2000)
        login_freq = random.randint(10, 50)
        account_age = random.randint(1, 100)

    data.append([
        posts,
        followers,
        following,
        login_freq,
        account_age,
        label
    ])

df = pd.DataFrame(data, columns=[
    "posts",
    "followers",
    "following",
    "login_freq",
    "account_age",
    "label"
])

df.to_csv("dataset.csv", index=False)

print("Dataset generated successfully!")
