from unittest.mock import patch

from django.test import TestCase

from weather.models import Location, WeatherObservation
from weather.ml.backtest import backtest_multiple_dates, backtest_temperature_forecast, calculate_historical_seasonal_mae
from weather.ml.evaluate import calculate_persistence_baseline, calculate_seasonal_baseline, evaluate_temperature_model
from weather.ml.features import (add_date_features, add_lag_features, add_rolling_features, 
                                    build_features, FEATURE_COLUMNS, get_latest_forecast_features, load_weather_data, 
                                    prepare_training_data, split_features_and_target, split_training_and_validation)
from weather.ml.forecast import generate_temperature_forecast
from weather.ml.models import create_temperature_model
from weather.ml.train import run_temperature_experiment, train_forecast_model, train_temperature_model

import pandas as pd
from datetime import date, timedelta

class LoadWeatherDataTests(TestCase):

    def setUp(self):
        self.location = Location.objects.create(
            open_meteo_id=12345,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
            country="United States",
            country_code="US",
            admin1="Illinois",
        )

    def test_load_weather_data(self):
        WeatherObservation.objects.create(
            location=self.location,
            date="2025-01-01",
            temperature_max=35.0,
            temperature_min=25.0,
            temperature_mean=30.0,
            precipitation_sum=0.1,
            rain_sum=0.1,
            snowfall_sum=0.0,
            wind_speed_max=15.0,
            wind_gusts_max=20.0,
            cloud_cover_mean=50.0,
            humidity_mean=70.0,
            pressure_mean=1010.0,
            weather_code=3,
        )

        data = load_weather_data(self.location.id)

        self.assertEqual(len(data), 1)
        self.assertEqual(data.iloc[0]["temperature_max"], 35.0)
        self.assertEqual(data.iloc[0]["temperature_min"], 25.0)
        self.assertEqual(data.iloc[0]["weather_code"], 3)

    def test_load_weather_data_empty(self):
        data = load_weather_data(self.location.id)

        self.assertTrue(data.empty)


class FeatureTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            open_meteo_id=12345,
            name="Chicago",
            latitude=41.8781,
            longitude=-87.6298,
            timezone="America/Chicago",
            country="United States",
            country_code="US",
            admin1="Illinois",
        )

        # multiple tests will fail unless we populate the table with observations
        for i in range(10):
            WeatherObservation.objects.create(
                location=self.location,
                date=date(2025, 1, 1) + timedelta(days=i),
                temperature_max=40 + i,
                temperature_min=20 + i,
                temperature_mean=30 + i,
                precipitation_sum=0,
                rain_sum=0,
                snowfall_sum=0,
                wind_speed_max=10,
                wind_gusts_max=15,
                cloud_cover_mean=50,
                humidity_mean=60,
                pressure_mean=1010,
                weather_code=0,
            )

    def test_add_date_features(self):
        data = pd.DataFrame(
            [
                {
                    "date": "2025-01-01",
                    "temperature_max": 35.0,
                }
            ]
        )

        data = add_date_features(data)

        self.assertEqual(data.iloc[0]["year"], 2025)
        self.assertEqual(data.iloc[0]["month"], 1)
        self.assertEqual(data.iloc[0]["day_of_year"], 1)

    def test_add_lag_features(self):
        data = pd.DataFrame(
            [
                {"date": "2025-01-01", "temperature_mean": 30.0, "precipitation_sum": 0.10, "humidity_mean": 70.0, "pressure_mean": 1010.0, "wind_speed_max": 15.0, "cloud_cover_mean": 50.0},
                {"date": "2025-01-02", "temperature_mean": 32.0, "precipitation_sum": 0.20, "humidity_mean": 72.0, "pressure_mean": 1011.0, "wind_speed_max": 16.0, "cloud_cover_mean": 55.0},
                {"date": "2025-01-03", "temperature_mean": 34.0, "precipitation_sum": 0.30, "humidity_mean": 74.0, "pressure_mean": 1012.0, "wind_speed_max": 17.0, "cloud_cover_mean": 60.0},
                {"date": "2025-01-04", "temperature_mean": 36.0, "precipitation_sum": 0.40, "humidity_mean": 76.0, "pressure_mean": 1013.0, "wind_speed_max": 18.0, "cloud_cover_mean": 65.0},
                {"date": "2025-01-05", "temperature_mean": 38.0, "precipitation_sum": 0.50, "humidity_mean": 78.0, "pressure_mean": 1014.0, "wind_speed_max": 19.0, "cloud_cover_mean": 70.0},
                {"date": "2025-01-06", "temperature_mean": 40.0, "precipitation_sum": 0.60, "humidity_mean": 80.0, "pressure_mean": 1015.0, "wind_speed_max": 20.0, "cloud_cover_mean": 75.0},
                {"date": "2025-01-07", "temperature_mean": 42.0, "precipitation_sum": 0.70, "humidity_mean": 82.0, "pressure_mean": 1016.0, "wind_speed_max": 21.0, "cloud_cover_mean": 80.0},
                {"date": "2025-01-08", "temperature_mean": 44.0, "precipitation_sum": 0.80, "humidity_mean": 84.0, "pressure_mean": 1017.0, "wind_speed_max": 22.0, "cloud_cover_mean": 85.0},
            ]
        )

        data = add_lag_features(data)

        self.assertTrue(pd.isna(data.iloc[0]["temperature_mean_lag_1"]))
        self.assertEqual(data.iloc[1]["temperature_mean_lag_1"], 30.0)
        self.assertEqual(data.iloc[7]["temperature_mean_lag_1"], 42.0)

        self.assertTrue(pd.isna(data.iloc[0]["temperature_mean_lag_7"]))
        self.assertTrue(pd.isna(data.iloc[6]["temperature_mean_lag_7"]))
        self.assertEqual(data.iloc[7]["temperature_mean_lag_7"], 30.0)

        self.assertTrue(pd.isna(data.iloc[0]["precipitation_sum_lag_1"]))
        self.assertEqual(data.iloc[1]["precipitation_sum_lag_1"], 0.10)
        self.assertEqual(data.iloc[7]["precipitation_sum_lag_1"], 0.70)

        self.assertTrue(pd.isna(data.iloc[0]["humidity_mean_lag_1"]))
        self.assertEqual(data.iloc[1]["humidity_mean_lag_1"], 70.0)
        self.assertEqual(data.iloc[7]["humidity_mean_lag_1"], 82.0)

        self.assertTrue(pd.isna(data.iloc[0]["pressure_mean_lag_1"]))
        self.assertEqual(data.iloc[1]["pressure_mean_lag_1"], 1010.0)
        self.assertEqual(data.iloc[7]["pressure_mean_lag_1"], 1016.0)

        self.assertTrue(pd.isna(data.iloc[0]["wind_speed_max_lag_1"]))
        self.assertEqual(data.iloc[1]["wind_speed_max_lag_1"], 15.0)
        self.assertEqual(data.iloc[7]["wind_speed_max_lag_1"], 21.0)

        self.assertTrue(pd.isna(data.iloc[0]["cloud_cover_mean_lag_1"]))
        self.assertEqual(data.iloc[1]["cloud_cover_mean_lag_1"], 50.0)
        self.assertEqual(data.iloc[7]["cloud_cover_mean_lag_1"], 80.0)

    def test_add_rolling_features(self):
        data = pd.DataFrame(
            [
                {"date": "2025-01-01", "temperature_mean": 30.0},
                {"date": "2025-01-02", "temperature_mean": 32.0},
                {"date": "2025-01-03", "temperature_mean": 34.0},
                {"date": "2025-01-04", "temperature_mean": 36.0},
                {"date": "2025-01-05", "temperature_mean": 38.0},
                {"date": "2025-01-06", "temperature_mean": 40.0},
                {"date": "2025-01-07", "temperature_mean": 42.0},
            ]
        )

        data = add_rolling_features(data)

        self.assertTrue(pd.isna(data.iloc[0]["temperature_mean_rolling_3"]))
        self.assertTrue(pd.isna(data.iloc[1]["temperature_mean_rolling_3"]))
        self.assertTrue(pd.isna(data.iloc[2]["temperature_mean_rolling_3"]))
        self.assertEqual(data.iloc[3]["temperature_mean_rolling_3"], 32.0)

        self.assertTrue(pd.isna(data.iloc[6]["temperature_mean_rolling_7"]))

    def test_build_features(self):

        data = build_features(self.location.id)

        expected_columns = [
            "date",
            "temperature_max",
            "temperature_min",
            "temperature_mean",
            "precipitation_sum",
            "rain_sum",
            "snowfall_sum",
            "wind_speed_max",
            "wind_gusts_max",
            "cloud_cover_mean",
            "humidity_mean",
            "pressure_mean",
            "weather_code",
            "year",
            "month",
            "day_of_year",
            "temperature_mean_lag_1",
            "temperature_mean_lag_7",
            "precipitation_sum_lag_1",
            "humidity_mean_lag_1",
            "pressure_mean_lag_1",
            "wind_speed_max_lag_1",
            "cloud_cover_mean_lag_1",
            "temperature_mean_rolling_3",
            "temperature_mean_rolling_7",
        ]

        for column in expected_columns:
            self.assertIn(column, data.columns)

    def test_prepare_training_data(self):
        data = build_features(self.location.id)
        training_data = prepare_training_data(data)

        self.assertIn("target_date", training_data.columns)

        self.assertEqual(
            training_data["target_date"].iloc[0],
            training_data["date"].iloc[0] + timedelta(days=1),
        )

        self.assertIn("target_temperature_mean", training_data.columns)

        self.assertEqual(
            training_data["target_temperature_mean"].iloc[0],
            training_data["temperature_mean"].iloc[1],
        )

        self.assertFalse(
            training_data["target_temperature_mean"].isna().any()
        )

    def test_split_features_and_target(self):
        data = build_features(self.location.id)
        data = prepare_training_data(data)

        X, y = split_features_and_target(data)

        self.assertNotIn("target_temperature_mean", X.columns)
        self.assertEqual(len(X), len(y))
        self.assertEqual(len(X.columns), 12)
        self.assertIn("temperature_mean", X.columns)
        self.assertEqual(y.name, "target_temperature_mean")

    def test_split_training_and_validation(self):
        data = build_features(self.location.id)
        data = prepare_training_data(data)
        X, y = split_features_and_target(data)

        X_train, X_validation, y_train, y_validation = (
            split_training_and_validation(X, y)
        )

        self.assertEqual(len(X_train), 1)
        self.assertEqual(len(X_validation), 1)
        self.assertEqual(len(y_train), 1)
        self.assertEqual(len(y_validation), 1)

        self.assertLess(
            X_train.index.max(),
            X_validation.index.min(),
        )

    def test_create_temperature_model(self):
        model = create_temperature_model()

        self.assertEqual(model.n_estimators, 200)
        self.assertEqual(model.random_state, 42)

    def test_train_temperature_model(self):
        model, X_validation, y_validation, _, _ = train_temperature_model(
            self.location.id
        )

        self.assertIsNotNone(model)
        self.assertEqual(len(X_validation), len(y_validation))
        self.assertEqual(len(X_validation), 1)

    def test_evaluate_temperature_model(self):
        model, X_validation, y_validation, _, _ = train_temperature_model(
            self.location.id
        )

        metrics = evaluate_temperature_model(
            model,
            X_validation,
            y_validation,
        )

        self.assertIn("mae", metrics)
        self.assertIsInstance(metrics["mae"], float)
        self.assertGreaterEqual(metrics["mae"], 0)
        self.assertIn("rmse", metrics)
        self.assertIsInstance(metrics["rmse"], float)
        self.assertGreaterEqual(metrics["rmse"], 0)
        self.assertIn("baseline_mae", metrics)
        self.assertIsInstance(metrics["baseline_mae"], float)
        self.assertGreaterEqual(metrics["baseline_mae"], 0)

    # confirms baseline can calculate valid (positive) MAE from same feature data used by forecasting pipeline
    def test_calculate_persistence_baseline(self):
        data = build_features(self.location.id)
        data = prepare_training_data(data)

        X, y = split_features_and_target(data)

        _, X_validation, _, y_validation = split_training_and_validation(
            X,
            y,
        )

        mae = calculate_persistence_baseline(
            X_validation,
            y_validation,
        )

        self.assertIsInstance(mae, float)
        self.assertGreaterEqual(mae, 0)
        self.assertAlmostEqual(mae, 1.0)    # b/c our 10 test observations increase by exactly 1 degree each day

    # Just verifies that the entire experiment runs
    def test_run_temperature_experiment(self):
        model, metrics = run_temperature_experiment(self.location.id)

        self.assertIsNotNone(model)
        self.assertIn("mae", metrics)
        self.assertIn("rmse", metrics)
        self.assertIn("baseline_mae", metrics)
        self.assertIn("seasonal_baseline_mae", metrics)

    # verifies same date across years being compared
    def test_calculate_seasonal_baseline(self):
        training_data = pd.DataFrame({
            "target_date": pd.to_datetime([
                "2023-01-10",
                "2024-01-10",
            ]),
            "target_temperature_mean": [20.0, 24.0],
        })

        validation_data = pd.DataFrame({
            "target_date": pd.to_datetime(["2025-01-10"]),
            "target_temperature_mean": [25.0],
        })

        mae = calculate_seasonal_baseline(
            training_data,
            validation_data,
        )

        self.assertAlmostEqual(mae, 3.0)

    # tests target construction not forecast accuracy
    # also: assumes observations recorded on consecutive dates
    def test_prepare_training_data_two_day_horizon(self):
        data = build_features(self.location.id)
        training_data = prepare_training_data(data, horizon=2)

        self.assertEqual(len(training_data), 1)

        self.assertEqual(
            training_data.iloc[0]["target_temperature_mean"],
            39.0,
        )

        self.assertEqual(
            training_data.iloc[0]["target_date"].date(),
            date(2025, 1, 10),
        )

    # extends existing 10-day test dataset to 30 days,
    # trains with a three-day horizon,
    # and checks that every training target is known by the first validation forecast date
    def test_train_temperature_model_prevents_target_leakage(self):
        for i in range(10, 30):
            WeatherObservation.objects.create(
                location=self.location,
                date=date(2025, 1, 1) + timedelta(days=i),
                temperature_mean=30 + i,
            )

        _, _, _, training_data, validation_data = train_temperature_model(
            self.location.id,
            horizon=3,
        )

        validation_start = pd.to_datetime(
            validation_data["date"].iloc[0]
        )

        self.assertFalse(training_data.empty)
        self.assertFalse(validation_data.empty)

        self.assertTrue(
            (training_data["target_date"] <= validation_start).all()
        )

    # verify that 1-day lag is NaN if we inserted a dummy row for missing day prior
    def test_build_features_handles_missing_dates(self):
        WeatherObservation.objects.filter(
            location=self.location,
            date=date(2025, 1, 9),
        ).delete()

        data = build_features(self.location.id)

        january_10 = data.loc[
            data["date"] == pd.Timestamp("2025-01-10")
        ].iloc[0]

        self.assertTrue(
            pd.isna(january_10["temperature_mean_lag_1"])
        )

    # Verify that inserted dummy rows for missing dates do not carry over to valid data
    def test_train_temperature_model_excludes_missing_features(self):
        for i in range(10, 30):
            WeatherObservation.objects.create(
                location=self.location,
                date=date(2025, 1, 1) + timedelta(days=i),
                temperature_mean=30 + i,
            )

        WeatherObservation.objects.filter(
            location=self.location,
            date=date(2025, 1, 15),
        ).delete()

        _, X_validation, _, training_data, validation_data = (
            train_temperature_model(self.location.id, horizon=3)
        )

        X_train, _ = split_features_and_target(training_data)

        self.assertFalse(X_train.isna().any().any())
        self.assertFalse(X_validation.isna().any().any())

        retained_dates = pd.concat(
            [training_data["date"], validation_data["date"]]
        )

        self.assertNotIn(
            pd.Timestamp("2025-01-16"),
            retained_dates.tolist(),
        )

    def test_train_temperature_model_requires_enough_data(self):
        WeatherObservation.objects.filter(
            location=self.location,
            date=date(2025, 1, 10),
        ).delete()

        with self.assertRaisesRegex(
            ValueError,
            "Not enough usable weather observations",   # Need at least 2!
        ):
            train_temperature_model(self.location.id)

    def test_get_latest_forecast_features(self):
        forecast_origin, X = get_latest_forecast_features(
            self.location.id
        )

        self.assertEqual(
            forecast_origin,
            pd.Timestamp("2025-01-10"),
        )
        self.assertEqual(len(X), 1)
        self.assertEqual(X.columns.tolist(), FEATURE_COLUMNS)
        self.assertFalse(X.isna().any().any())

    # Verifies experiment fails if latest observation data missing (want complete inputs for predictions)
    # -- deleting 1/9/25 observation means 1/10/25 1-day lag is missing
    def test_get_latest_forecast_features_rejects_missing_features(self):
        WeatherObservation.objects.filter(
            location=self.location,
            date=date(2025, 1, 9),
        ).delete()

        with self.assertRaisesRegex(
            ValueError,
            "The latest observation has missing forecast features",
        ):
            get_latest_forecast_features(self.location.id)

    def test_train_forecast_model_one_day_horizon(self):
        model = train_forecast_model(self.location.id, horizon=1)

        forecast_origin, X = get_latest_forecast_features(
            self.location.id
        )

        predictions = model.predict(X)

        self.assertEqual(forecast_origin, pd.Timestamp("2025-01-10"))
        self.assertEqual(len(predictions), 1)
        self.assertTrue(pd.notna(predictions[0]))

    def test_train_forecast_model_two_day_horizon(self):
        model = train_forecast_model(self.location.id, horizon=2)

        forecast_origin, X = get_latest_forecast_features(
            self.location.id
        )

        predictions = model.predict(X)

        self.assertEqual(
            forecast_origin + pd.Timedelta(days=2),
            pd.Timestamp("2025-01-12"),
        )
        self.assertEqual(len(predictions), 1)
        self.assertTrue(pd.notna(predictions[0]))

    # tests function works with minimum horizon
    def test_generate_temperature_forecast(self):
        predictions = generate_temperature_forecast(
            self.location.id,
            days=2,
        )

        self.assertEqual(len(predictions), 2)

        self.assertEqual(
            [prediction["date"] for prediction in predictions],
            [
                pd.Timestamp("2025-01-11"),
                pd.Timestamp("2025-01-12"),
            ],
        )

        for prediction in predictions:
            self.assertIsInstance(prediction["temperature_mean"], float)
            self.assertTrue(pd.notna(prediction["temperature_mean"]))

    def test_generate_temperature_forecast_rejects_invalid_days(self):
        with self.assertRaisesRegex(
            ValueError,
            "Forecast days must be at least 1",
        ):
            generate_temperature_forecast(self.location.id, days=0)

    def test_train_forecast_model_respects_as_of_date(self):
        for i in range(10, 30):
            WeatherObservation.objects.create(
                location=self.location,
                date=date(2025, 1, 1) + timedelta(days=i),
                temperature_mean=30 + i,
            )

        with patch("weather.ml.train.create_temperature_model") as mock_factory:
            train_forecast_model(
                self.location.id,
                horizon=3,
                as_of=date(2025, 1, 20),
            )

            X_train, y_train = mock_factory.return_value.fit.call_args.args

        self.assertFalse(X_train.empty)
        self.assertEqual(len(X_train), len(y_train))

        # January 17 is the latest possible input date:
        # its three-day-ahead target is January 20.
        self.assertLessEqual(X_train.index.max(), 16)

    def test_get_latest_forecast_features_respects_as_of_date(self):
        forecast_origin, X = get_latest_forecast_features(
            self.location.id,
            as_of=date(2025, 1, 9),
        )

        self.assertEqual(
            forecast_origin,
            pd.Timestamp("2025-01-09"),
        )
        self.assertEqual(len(X), 1)
        self.assertEqual(X.columns.tolist(), FEATURE_COLUMNS)

    # Tests backtest's date matching and error calculations w/o training models
    # - mocked observations give absolute errors of 2 degrees on both days
    def test_generate_temperature_forecast_respects_as_of_date(self):
        with patch("weather.ml.forecast.train_forecast_model") as mock_train:
            mock_train.return_value.predict.return_value = [30.0]

            predictions = generate_temperature_forecast(
                self.location.id,
                days=2,
                as_of=date(2025, 1, 9),
            )

        self.assertEqual(
            [prediction["date"] for prediction in predictions],
            [
                pd.Timestamp("2025-01-10"),
                pd.Timestamp("2025-01-11"),
            ],
        )

        self.assertEqual(mock_train.call_count, 2)
        mock_train.assert_any_call(
            self.location.id,
            horizon=1,
            as_of=pd.Timestamp("2025-01-09"),
        )
        mock_train.assert_any_call(
            self.location.id,
            horizon=2,
            as_of=pd.Timestamp("2025-01-09"),
        )

    def test_backtest_temperature_forecast(self):
        predictions = [
            {
                "date": pd.Timestamp("2025-01-09"),
                "temperature_mean": 40.0,
            },
            {
                "date": pd.Timestamp("2025-01-10"),
                "temperature_mean": 37.0,
            },
        ]

        with (
            patch(
                "weather.ml.backtest.generate_temperature_forecast",
                return_value=predictions,
            ) as mock_forecast,
            patch(
                "weather.ml.backtest.calculate_historical_seasonal_mae",
                return_value=3.0,
            ),
        ):
            metrics = backtest_temperature_forecast(
                self.location.id,
                as_of=date(2025, 1, 8),
                days=2,
            )

        mock_forecast.assert_called_once_with(
            self.location.id,
            days=2,
            as_of=date(2025, 1, 8),
        )

        self.assertEqual(metrics["days_evaluated"], 2)
        self.assertAlmostEqual(metrics["mae"], 2.0)
        self.assertAlmostEqual(metrics["rmse"], 2.0)
        self.assertAlmostEqual(metrics["seasonal_baseline_mae"], 3.0)

    # as_of set for (UP TO) 1/10/2025 so if only date is in the future (1/11/2025), it should be rejected
    def test_backtest_temperature_forecast_rejects_missing_observations(self):
        predictions = [
            {
                "date": pd.Timestamp("2025-01-11"),
                "temperature_mean": 35.0,
            },
        ]

        with patch(
            "weather.ml.backtest.generate_temperature_forecast",
            return_value=predictions,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Missing observed temperature for 2025-01-11",
            ):
                backtest_temperature_forecast(
                    self.location.id,
                    as_of=date(2025, 1, 10),
                    days=1,
                )

    def test_backtest_multiple_dates(self):
        as_of_dates = [
            date(2025, 1, 8),
            date(2025, 1, 9),
        ]

        with patch(
            "weather.ml.backtest.backtest_temperature_forecast"
        ) as mock_backtest:
            mock_backtest.side_effect = [
                {"days_evaluated": 2, "mae": 2.0, "rmse": 2.5},
                {"days_evaluated": 2, "mae": 3.0, "rmse": 3.5},
            ]

            results = backtest_multiple_dates(
                self.location.id,
                as_of_dates,
                days=2,
            )

        self.assertEqual(len(results), 2)
        self.assertEqual(
            [result["as_of"] for result in results],
            as_of_dates,
        )
        self.assertEqual(
            [result["mae"] for result in results],
            [2.0, 3.0],
        )
        self.assertEqual(mock_backtest.call_count, 2)
        mock_backtest.assert_any_call(
            self.location.id,
            as_of=as_of_dates[0],
            days=2,
        )
        mock_backtest.assert_any_call(
            self.location.id,
            as_of=as_of_dates[1],
            days=2,
        )

    def test_calculate_historical_seasonal_mae(self):
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2024, 1, 9),
            temperature_mean=35.0,
        )
        WeatherObservation.objects.create(
            location=self.location,
            date=date(2024, 1, 10),
            temperature_mean=37.0,
        )

        predictions = [
            {
                "date": pd.Timestamp("2025-01-09"),
                "temperature_mean": 40.0,
            },
            {
                "date": pd.Timestamp("2025-01-10"),
                "temperature_mean": 40.0,
            },
        ]

        mae = calculate_historical_seasonal_mae(
            self.location.id,
            as_of=date(2025, 1, 8),
            predictions=predictions,
        )

        self.assertAlmostEqual(mae, 2.5)