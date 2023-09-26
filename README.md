# Automated Momentum Trading Experiment

This is a Python script for implementing a momentum trading strategy using the Deriv.com API. The script buys and sells assets based on their recent performance, as measured by price changes over a specified time frame. The strategy also includes risk management logic to help prevent large losses.

## Dependencies

Before running the script, you'll need to install the following dependencies:

- requests
- numpy
- pandas
- deriv-api

You can install them all at once using the requirements.txt file with the following command:

```
pip install -r requirements.txt
```

## Environment Variables

The code requires some environment variables to work, to see the required variables please look at the .env-example file.

Create a .env file, and fill in the required environment variables which can be creating a sample deriv app.

To see how the create an application on deriv, please have a look at the following documentation.

https://api.deriv.com/docs/setting-up-a-deriv-application#:~:text=How%20to%20create%20a%20Deriv%20application%E2%80%8B,in%20the%20Manage%20Applications%20tab.

# Running the Script

Run the code using the following command

```
python main.py -t <profit amount before closing trade> -s <symbol> -p <amount for buying proposal> -a <amount to realize on > -d <duration for holding contract>
```

example

```
python src/main.py -t 20 -s 1HZ75V -p 1 -a 4 -d 720
```

Make sure to replace the placeholders (<profit amount before closing trade>, <symbol>, etc.) with the appropriate values for your trading strategy.

# Deploying the code

- Create an AWS account, and create an EC2 instance “A t3 micro instance should be sufficient.”
- Login to the provisioned EC2 instance.
- Clone the GitHub repository containing the momentum trading code onto the EC2 instance.
  \*Install the necessary dependencies using the requirements.txt file provided in the repository.
  This can be done using the `pip -r install requirements.txt`.
- Run the momentum trading script using the following command
  python main.py -target <profit amount before closing trade> -s <symbol> -p <amount for buying proposal> -a <amount to realize on > -d <duration for holding contract>

Additional Notes
This script is designed for educational purposes only and should not be used for actual trading without extensive testing and modification.
For more information on how the momentum trading strategy works and how the script is implemented, please refer to the blog post linked in the repository's description.

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
