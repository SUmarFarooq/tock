**Project Info**
----
To fetch a list of all users who have not submitted a timecard for the specified period.

* **URL**

  /reporting_period_audit/[YYYY-MM-DD].json
  
  *The value [YYYY-MM-DD] is the `start_date` attribute of the reporting period sought. For a list of reporting periods, please see the [/reporting_period_audit.json documentation](https://github.com/18F/tock/blob/master/api-docs/reporting-period-audit.md).*

* **Method:**

  `GET`
  
*  **URL Params**

   **Required:**
   None.
   
   **Optional:**
   None.

* **Success Response:**

  * **Code:** `200` <br />
    **Content:** 
```
[
    {
        "id": 77,
        "username": "john.smith",
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.scott@abc"
    },...
```
 
* **Error Response:**

  * **Code:** `401 UNAUTHORIZED` <br />
    **Content:** `{"detail":"Authentication credentials were not provided."}`

* **Sample Call:**

```
$ curl https://tock.18f.gov/api/reporting_period_audit/2016-09-18.json -H 'Authorization: Token randomalphanumericstringed854b18ba024327'
```

* **Notes:** None.
 
