import clsx from 'clsx'

interface SkeletonProps {
  width?: string | number
  height?: string | number
  circle?: boolean
  count?: number
  className?: string
}

export const Skeleton = ({
  width,
  height = '1rem',
  circle = false,
  count = 1,
  className,
}: SkeletonProps) => {
  const skeletons = Array(count).fill(null)

  return (
    <>
      {skeletons.map((_, index) => (
        <div
          key={index}
          className={clsx('skeleton', { 'skeleton-circle': circle }, className)}
          style={{
            width: width || '100%',
            height,
            marginBottom: count > 1 ? '0.5rem' : undefined,
          }}
        />
      ))}
    </>
  )
}

// Skeleton variations for common use cases
export const SkeletonKPICard = () => (
  <div className="kpi-card">
    <Skeleton circle width={48} height={48} />
    <div style={{ flex: 1 }}>
      <Skeleton width="60%" height="2rem" />
      <Skeleton width="80%" height="1rem" />
    </div>
  </div>
)

export const SkeletonTable = ({ rows = 5 }: { rows?: number }) => (
  <div className="table-wrapper">
    <table className="data-table">
      <thead>
        <tr>
          {[1, 2, 3, 4, 5].map((i) => (
            <th key={i}>
              <Skeleton width="80%" height="0.875rem" />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array(rows)
          .fill(null)
          .map((_, rowIndex) => (
            <tr key={rowIndex}>
              {[1, 2, 3, 4, 5].map((colIndex) => (
                <td key={colIndex}>
                  <Skeleton width="90%" />
                </td>
              ))}
            </tr>
          ))}
      </tbody>
    </table>
  </div>
)

export const SkeletonDeviceCard = () => (
  <div className="device-type-card">
    <Skeleton width="70%" height="1.125rem" />
    <div style={{ marginTop: '1rem' }}>
      <Skeleton width="100%" height="2rem" />
    </div>
    <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem' }}>
      <Skeleton width="30%" />
      <Skeleton width="30%" />
      <Skeleton width="30%" />
    </div>
  </div>
)

export const SkeletonChart = () => (
  <div className="card">
    <div className="card-header">
      <Skeleton width="200px" height="1.25rem" />
    </div>
    <div className="card-content" style={{ height: '300px' }}>
      <Skeleton width="100%" height="100%" />
    </div>
  </div>
)
