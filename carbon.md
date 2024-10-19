# Carbon Footprint Calculation from Utility Bills

Carbon footprint from utility bills (e.g., electricity, gas, water, and fuel) is calculated by converting the energy consumed into the equivalent amount of carbon dioxide (CO2) emissions. This is done using **emission factors**, which represent the amount of CO2 emitted per unit of energy used for each type of utility.

## 1. **Electricity**:
- **Step 1**: Determine the total energy consumption from your bill (measured in kilowatt-hours, kWh).
- **Step 2**: Use the **electricity emission factor**, which is the amount of CO2 emitted per kWh. This varies depending on the energy source used (e.g., coal, natural gas, or renewable sources).
    - Example: If the emission factor is 0.92 kg CO2/kWh, and you used 500 kWh:
      ```
      Carbon Footprint = 500 kWh × 0.92 kg CO2/kWh = 460 kg CO2
      ```

## 2. **Natural Gas**:
- **Step 1**: Determine the gas consumption from your bill (measured in cubic meters or therms).
- **Step 2**: Use the **natural gas emission factor** (usually around 2.204 kg CO2 per cubic meter or 5.3 kg CO2 per therm).
    - Example: If you consumed 100 cubic meters of natural gas:
      ```
      Carbon Footprint = 100 m³ × 2.204 kg CO2/m³ = 220.4 kg CO2
      ```

## 3. **Water**:
- **Step 1**: Water itself doesn’t emit CO2, but the energy used to treat, transport, and heat water can. The energy consumption for this is typically factored in (usually measured in kWh).
- **Step 2**: Use the emission factor associated with the electricity used to pump and heat the water.
    - Example: For every cubic meter of water, around 0.34 kWh of electricity may be required. If the emission factor for electricity is 0.92 kg CO2/kWh:
      ```
      Carbon Footprint = 0.34 kWh/m³ × 0.92 kg CO2/kWh = 0.312 kg CO2 per m³ of water
      ```
    - Multiply this by the total water consumption to get the footprint.

## 4. **Fuel (Heating, Vehicles)**:
- **Step 1**: Determine the amount of fuel used (usually in liters or gallons for gasoline/diesel, or cubic meters for heating oil or propane).
- **Step 2**: Use the **fuel-specific emission factor** (for gasoline: ~2.31 kg CO2 per liter, for diesel: ~2.68 kg CO2 per liter).
    - Example: If 50 liters of gasoline were used:
      ```
      Carbon Footprint = 50 liters × 2.31 kg CO2/liter = 115.5 kg CO2
      ```

## **Fuel (Total Carbon Footprint)**:
- The total carbon footprint from utility bills is the sum of the carbon footprints for each utility type (electricity, gas, water, fuel):
    ```
    - Total Carbon Footprint = Electricity Footprint + Gas Footprint + Water Footprint + Fuel Footprint

## Emission Factors:
- **Electricity**: Varies by energy source (coal, renewable, etc.). A general range is **0.3–1.0 kg CO2 per kWh**.
- **Natural Gas**: ~**2.204 kg CO2 per cubic meter** or **5.3 kg CO2 per therm**.
- **Water**: Depends on the region, typically a few grams of CO2 per liter or cubic meter.
- **Fuel**: Gasoline ~**2.31 kg CO2 per liter**, Diesel ~**2.68 kg CO2 per liter**.

## Conclusion:
By applying the correct emission factors based on the type and quantity of utility usage, the carbon footprint can be calculated for each utility and aggregated to provide a total footprint for a household or organization.
