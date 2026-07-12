import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import './App.css'

function useFetchData(url) {
  const [data, setData] = useState([])

  useEffect(() => {
    fetch(url)
      .then((response) => response.json())
      .then((result) => setData(result))
      .catch((error) => console.error(`Fetch failed for ${url}:`, error))
  }, [url])

  return data
}

const COLORS = ['#FF5A1F', '#1D4E89', '#17A398', '#F2B705', '#7B61FF', '#5B5F7A']

function App() {
  const cityData = useFetchData('http://127.0.0.1:8000/stats/city-wise')
  const categoryData = useFetchData('http://127.0.0.1:8000/stats/category-wise')
  const sourceData = useFetchData('http://127.0.0.1:8000/stats/source-wise')
  const allListings = useFetchData('http://127.0.0.1:8000/listings')

  function downloadCSV(data) {
    if (!data.length) return

    const headers = Object.keys(data[0])
    const csvRows = [
      headers.join(","),
      ...data.map((row) =>
        headers.map((field) => `"${(row[field] ?? "").toString().replace(/"/g, '""')}"`).join(",")
      ),
    ]
    const csvContent = csvRows.join("\n")

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.setAttribute("download", "business_listings.csv")
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const totalListings = cityData.reduce((sum, item) => sum + item.count, 0)

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="eyebrow">
          <span className="status-dot" />
          DIRECTORY DATA · SULEKHA
        </div>
        <h1>Business Listings Dashboard</h1>
        <p>Aggregated insights from scraped business directory data</p>
        <div className="route-rule" aria-hidden="true" />
      </header>

      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-value">{totalListings}</span>
          <span className="stat-label">Total Listings</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{cityData.length}</span>
          <span className="stat-label">Cities</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{categoryData.length}</span>
          <span className="stat-label">Categories</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{sourceData.length}</span>
          <span className="stat-label">Sources</span>
        </div>
      </div>

      <div className="chart-grid">
        <div className="chart-card">
          <h2>City-wise Counts</h2>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={cityData}>
              <XAxis dataKey="label" stroke="#5B5F7A" fontSize={12} />
              <YAxis stroke="#5B5F7A" fontSize={12} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #E4E6ED' }} />
              <Bar dataKey="count" fill="#FF5A1F" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card category-card">
            <h2>Category-wise Counts</h2>
            <div className="category-layout">
              <ResponsiveContainer width="100%" height={280} className="category-chart">
                <PieChart>
                  <Pie
                    data={categoryData}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={105}
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={entry.label} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #E4E6ED' }} />
                </PieChart>
              </ResponsiveContainer>

              <ul className="category-legend">
                {categoryData.map((entry, index) => (
                  <li key={entry.label}>
                    <span
                      className="legend-swatch"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="legend-label">{entry.label}</span>
                    <span className="legend-count">{entry.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

        <div className="chart-card">
          <h2>Source-wise Counts</h2>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={sourceData}>
              <XAxis dataKey="label" stroke="#5B5F7A" fontSize={12} />
              <YAxis stroke="#5B5F7A" fontSize={12} />
              <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #E4E6ED' }} />
              <Bar dataKey="count" fill="#1D4E89" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
        <div className="chart-card listings-table-card">
        <div className="table-header">
          <h2>All Listings ({allListings.length})</h2>
          <button className="download-btn" onClick={() => downloadCSV(allListings)}>
            Download CSV
          </button>
        </div>

        <div className="table-scroll">
          <table className="listings-table">
            <thead>
              <tr>
                <th>Business Name</th>
                <th>Category</th>
                <th>City</th>
                <th>Phone</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {allListings.map((listing) => (
                <tr key={listing.id}>
                  <td>{listing.business_name}</td>
                  <td>{listing.category}</td>
                  <td>{listing.city}</td>
                  <td>{listing.phone || "—"}</td>
                  <td>{listing.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default App