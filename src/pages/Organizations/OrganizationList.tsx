import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  Alert
} from '@mui/material';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Add as AddIcon,
  Search as SearchIcon,
  MoreVert as MoreIcon,
  Business as BusinessIcon,
  Block as BlockIcon,
  Edit as EditIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { Organization } from '../../types';
import api from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

const OrganizationList: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [suspendDialogOpen, setSuspendDialogOpen] = useState(false);
  const [suspendReason, setSuspendReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['organizations', statusFilter, searchQuery],
    queryFn: async () => {
      const params: any = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (searchQuery) params.search = searchQuery;
      return await api.getOrganizations(params);
    }
  });

  const suspendMutation = useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      return await api.suspendOrganization(id, reason);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] });
      setSuspendDialogOpen(false);
      setSuspendReason('');
      setSelectedOrg(null);
    }
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, org: Organization) => {
    setAnchorEl(event.currentTarget);
    setSelectedOrg(org);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleSuspend = () => {
    if (selectedOrg?.id && suspendReason) {
      suspendMutation.mutate({ id: selectedOrg.id, reason: suspendReason });
    }
  };

  const getStatusChip = (status: string) => {
    const statusConfig = {
      active: { color: 'success', label: 'Active' },
      trial: { color: 'info', label: 'Trial' },
      suspended: { color: 'error', label: 'Suspended' },
      inactive: { color: 'default', label: 'Inactive' },
      pending_approval: { color: 'warning', label: 'Pending' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.inactive;
    
    return (
      <Chip
        label={config.label}
        color={config.color as any}
        size="small"
      />
    );
  };

  const getPlanChip = (plan: string) => {
    const planConfig = {
      free_trial: { color: 'default', label: 'Free Trial' },
      basic: { color: 'primary', label: 'Basic' },
      professional: { color: 'secondary', label: 'Professional' },
      enterprise: { color: 'success', label: 'Enterprise' },
      custom: { color: 'info', label: 'Custom' }
    };

    const config = planConfig[plan as keyof typeof planConfig] || planConfig.basic;
    
    return (
      <Chip
        label={config.label}
        color={config.color as any}
        size="small"
        variant="outlined"
      />
    );
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Organization',
      flex: 1,
      minWidth: 200,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <BusinessIcon sx={{ mr: 1, color: 'text.secondary' }} />
          <Box>
            <Typography variant="body2">{params.value}</Typography>
            <Typography variant="caption" color="text.secondary">
              {params.row.type}
            </Typography>
          </Box>
        </Box>
      )
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params: GridRenderCellParams) => getStatusChip(params.value)
    },
    {
      field: 'billing_plan',
      headerName: 'Plan',
      width: 130,
      renderCell: (params: GridRenderCellParams) => getPlanChip(params.value)
    },
    {
      field: 'current_users',
      headerName: 'Users',
      width: 100,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.value}/{params.row.max_users}
        </Typography>
      )
    },
    {
      field: 'claims_this_month',
      headerName: 'Claims/Month',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2">
          {params.value}/{params.row.max_claims_per_month}
        </Typography>
      )
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 120,
      renderCell: (params: GridRenderCellParams) => 
        format(new Date(params.value), 'MMM d, yyyy')
    },
    {
      field: 'actions',
      headerName: '',
      width: 60,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => (
        <IconButton
          size="small"
          onClick={(e) => handleMenuOpen(e, params.row)}
        >
          <MoreIcon />
        </IconButton>
      )
    }
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Organizations</Typography>
        {hasPermission('org:create') && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/organizations/new')}
          >
            Add Organization
          </Button>
        )}
      </Box>

      <Paper sx={{ mb: 2, p: 2 }}>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Search organizations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
          <FormControl sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="trial">Trial</MenuItem>
              <MenuItem value="suspended">Suspended</MenuItem>
              <MenuItem value="pending_approval">Pending</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      <Paper>
        <DataGrid
          rows={data?.data || []}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 10 },
            },
          }}
          pageSizeOptions={[10, 25, 50]}
          loading={isLoading}
          autoHeight
          disableRowSelectionOnClick
        />
      </Paper>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => {
          navigate(`/organizations/${selectedOrg?.id}`);
          handleMenuClose();
        }}>
          <BusinessIcon sx={{ mr: 1 }} fontSize="small" />
          View Details
        </MenuItem>
        {hasPermission('org:update') && (
          <MenuItem onClick={() => {
            navigate(`/organizations/${selectedOrg?.id}/edit`);
            handleMenuClose();
          }}>
            <EditIcon sx={{ mr: 1 }} fontSize="small" />
            Edit
          </MenuItem>
        )}
        <MenuItem onClick={() => {
          navigate(`/organizations/${selectedOrg?.id}/stats`);
          handleMenuClose();
        }}>
          <AssessmentIcon sx={{ mr: 1 }} fontSize="small" />
          View Stats
        </MenuItem>
        {hasPermission('org:suspend') && selectedOrg?.status !== 'suspended' && (
          <MenuItem onClick={() => {
            setSuspendDialogOpen(true);
            handleMenuClose();
          }}>
            <BlockIcon sx={{ mr: 1 }} fontSize="small" />
            Suspend
          </MenuItem>
        )}
      </Menu>

      <Dialog open={suspendDialogOpen} onClose={() => setSuspendDialogOpen(false)}>
        <DialogTitle>Suspend Organization</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Suspending an organization will prevent all users from accessing the system.
          </Alert>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Organization: <strong>{selectedOrg?.name}</strong>
          </Typography>
          <TextField
            fullWidth
            label="Reason for suspension"
            multiline
            rows={3}
            value={suspendReason}
            onChange={(e) => setSuspendReason(e.target.value)}
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSuspendDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSuspend}
            color="error"
            variant="contained"
            disabled={!suspendReason || suspendMutation.isPending}
          >
            Suspend
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default OrganizationList;