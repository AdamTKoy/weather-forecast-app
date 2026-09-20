# RandomForestRegressor predicts by averaging outputs of multiple decision trees built using bootstrap samples (sub-samples with replacement)
# Usage:
# -> create_temperature_model.fit(x_training_data, y_training_data)
# -> create_temperature_model.predict(X_test_data)
from sklearn.ensemble import RandomForestRegressor

def create_temperature_model():
    return RandomForestRegressor(
        n_estimators=200,   # number of trees, default is 100
        random_state=42,    # control for reproducibility
        # can also specify:
        # - max_depth (of each tree)
        # - criterion (function used to measure split quality, ex: squared_error)
    )