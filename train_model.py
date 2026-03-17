import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# load dataset
data = pd.read_csv("dataset.csv")

X = data[[
    "msg_freq",
    "follow_rate",
    "duplicate_ratio",
    "login_freq",
    "engagement_rate",
    "suspicious_ratio"
]]
y = data["label"]

# split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# train model
model = RandomForestClassifier(n_estimators=100)

model.fit(X_train, y_train)

y_pred = model.predict(X_test)

# evaluate
accuracy = model.score(X_test, y_test)
print("Model Accuracy:", accuracy)

# save model
joblib.dump(model, "fake_account_model.pkl")
