import { Router } from 'express';
import * as controller from '../controllers/conflictController';

const router = Router();

router.get('/', controller.getAllConflicts);
router.get('/stats', controller.getStats);
router.get('/:id', controller.getConflictById);
router.post('/', controller.createConflict);
router.patch('/:id', controller.updateConflict);
router.delete('/:id', controller.deleteConflict);

export default router;
